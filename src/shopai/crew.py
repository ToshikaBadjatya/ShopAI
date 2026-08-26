import json
import re

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from shopai.llm import default_llm
from shopai.prompts import (
    PLANNING_PROMPT_TEMPLATE,
    PLANNING_SYSTEM_TEMPLATE,
    RECOMMENDATION_SYSTEM_TEMPLATE,
    RECOMMENDATION_PROMPT_TEMPLATE,
    VISUALIZE_SYSTEM_TEMPLATE,
    VISUALIZE_PROMPT_TEMPLATE,
)
from shopai.tools.outfit_scraper_tool import OutfitScraperTool
from shopai.tools.validation_tools import validate_request
from shopai.tools.outfit_visualization_tool import OutfitVisualizationTool
from shopai.tools.weather_tool import WeatherByLocationTool


@CrewBase
class Shopai():
    """Shopai crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    # ------------------------------------------------------------------
    # Agent definitions (used by both the full crew and step methods)
    # ------------------------------------------------------------------

    @agent
    def planning_agent(self) -> Agent:
        return Agent(
            llm=default_llm(),
            config=self.agents_config['planning_agent'],  # type: ignore[index]
            tools=[WeatherByLocationTool()],
            system_template=PLANNING_SYSTEM_TEMPLATE,
            prompt_template=PLANNING_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    @agent
    def recommendation_agent(self) -> Agent:
        return Agent(
            llm=default_llm(),
            config=self.agents_config['recommendation_agent'],  # type: ignore[index]
            tools=[OutfitScraperTool()],
            system_template=RECOMMENDATION_SYSTEM_TEMPLATE,
            prompt_template=RECOMMENDATION_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    @agent
    def marketplace_agent(self) -> Agent:
        # Stub agent — no tools/prompt templates defined yet.
        return Agent(
            llm=default_llm(),
            config=self.agents_config['marketplace_agent'],  # type: ignore[index]
            tools=[],
            verbose=True
        )

    @agent
    def visualize_agent(self) -> Agent:
        return Agent(
            llm=default_llm(),
            config=self.agents_config['visualize_agent'],  # type: ignore[index]
            tools=[OutfitVisualizationTool()],
            system_template=VISUALIZE_SYSTEM_TEMPLATE,
            prompt_template=VISUALIZE_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    # ------------------------------------------------------------------
    # Task definitions (used by the full sequential crew)
    # ------------------------------------------------------------------

    @task
    def planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['planning_task'],  # type: ignore[index]
        )

    @task
    def recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config['recommendation_task'],  # type: ignore[index]
            context=[self.planning_task()],
        )

    @task
    def visualize_task(self) -> Task:
        return Task(
            config=self.tasks_config['visualize_task'],  # type: ignore[index]
            context=[self.planning_task(), self.recommendation_task()],
            output_file='src/shopai/output/shopping_guide.md'
        )

    # ------------------------------------------------------------------
    # Full sequential crew (original behaviour preserved)
    # ------------------------------------------------------------------

    @crew
    def crew(self) -> Crew:
        """Creates the Shopai crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )

    # ==================================================================
    # HITL step methods
    # ==================================================================

    # ==================================================================
    # Architecture agents (validator / master / reviewer)
    #
    # Deliberately NOT decorated with @agent or @task: CrewBase collects
    # decorated members into self.agents and self.tasks, which is what crew()
    # above is built from. Leaving these plain keeps that crew as it was.
    # Note also that a task config naming an undecorated agent raises a
    # KeyError at class construction - so their task configs carry no `agent:`.
    # ==================================================================

    def recommendation_master_agent(self) -> Agent:
        """Manager of the recommendation crew - delegates, never executes."""
        return Agent(
            llm=default_llm(),
            config=self.agents_config['recommendation_master_agent'],  # type: ignore[index]
            tools=[],
            allow_delegation=True,
            verbose=True,
        )

    def review_recommendation_agent(self) -> Agent:
        """Second pass over the curated recommendations."""
        return Agent(
            llm=default_llm(),
            config=self.agents_config['review_recommendation_agent'],  # type: ignore[index]
            tools=[],
            verbose=True,
        )

    def recommendation_crew(self) -> Crew:
        """Hierarchical crew: the master routes work to the specialists.

        CrewAI requires the manager to sit outside the agents list.
        """
        return Crew(
            agents=[
                self.recommendation_agent(),
                self.review_recommendation_agent(),
                self.visualize_agent(),
            ],
            tasks=[
                Task(config=self.tasks_config['master_recommendation_task']),  # type: ignore[index]
                Task(config=self.tasks_config['review_recommendation_task']),  # type: ignore[index]
            ],
            process=Process.hierarchical,
            manager_agent=self.recommendation_master_agent(),
            verbose=True,
        )

    # ==================================================================
    # Guardrail
    # ==================================================================

    def run_validation(self, prompt: str) -> dict:
        """Guardrail. Runs the validation tools directly - no agent, no LLM.

        Kept as a method so callers do not have to care that the check stopped
        being agentic.

        Returns:
            {"intent": ..., "reason": ..., "clarification": ..., "findings": {...}}
        """
        return validate_request(prompt)

    def run_master_recommendation(self, prompt: str, profile: dict | None = None) -> dict:
        """Hand a request to the Recommendation Master crew.

        The master reads the request and decides which specialists run - the
        API does not route by intent any more.

        Returns:
            {"recommendations": [...], "summary": "...", "raw": "..."}
        """
        profile = profile or {}
        styles = profile.get("styles") or []
        inputs = {
            "shopping_request": prompt,
            "location": "India",
            "budget": "5000 INR",
            "gender": profile.get("gender") or "female",
            "height": profile.get("height") or "5'6\"",
            "body_type": profile.get("bodyType") or "average",
            "style": ", ".join(styles) or "casual",
        }

        raw = str(self.recommendation_crew().kickoff(inputs=inputs))
        return self._parse_recommendation_crew_output(raw)

    def _parse_recommendation_crew_output(self, raw: str) -> dict:
        """The manager writes prose as often as JSON - keep whichever we get."""
        parsed = self._extract_json_from_text(raw)

        if isinstance(parsed, dict) and isinstance(parsed.get("recommendations"), list):
            return {"recommendations": parsed["recommendations"], "summary": "", "raw": raw}

        if isinstance(parsed, list):
            return {"recommendations": parsed, "summary": "", "raw": raw}

        return {"recommendations": [], "summary": raw.strip(), "raw": raw}

    def run_planning(self, inputs: dict) -> dict:
        """Run only the planning agent/task.

        Args:
            inputs: dict with keys shopping_request, location, budget,
                    gender, height, body_type, style.

        Returns:
            {
                "outfits": [...],   # list parsed from the agent JSON output
                "weather": {},      # weather dict if embedded in output, else {}
                "raw": "..."        # full raw string returned by the agent
            }
        """
        description = (
            "Fetch the current weather for {location} using the weather_by_location tool.\n"
            "Create a comprehensive shopping plan for: {shopping_request}\n"
            "Consider the user's gender ({gender}), body type ({body_type}), "
            "height ({height}), style ({style}), and any stated preferences.\n"
            "Use the weather to suggest appropriate clothing and accessories.\n"
            "Stay within the budget of {budget}."
        ).format(**inputs)

        t = Task(
            description=description,
            expected_output=(
                "Return a JSON array of outfit suggestions based on the shopping request. "
                "Each item must include outfit_name, items, rationale, and weather_context."
            ),
            agent=self.planning_agent(),
        )

        single_crew = Crew(
            agents=[self.planning_agent()],
            tasks=[t],
            process=Process.sequential,
            verbose=True,
        )

        result = single_crew.kickoff(inputs=inputs)
        raw = str(result)
        parsed = self._parse_planning_output(raw)
        return parsed

    def run_recommendation(
        self,
        inputs: dict,
        planning_output: dict,
        approved_outfit_indices: list = None,
    ) -> dict:
        """Run only the recommendation agent/task.

        Args:
            inputs: same input dict as run_planning.
            planning_output: dict returned by run_planning.
            approved_outfit_indices: optional list of int indices selecting
                which outfits from planning_output["outfits"] to pass on.
                If None, all outfits are used.

        Returns:
            {
                "recommendations": [{"outfit_name": ..., "products": [...]}, ...],
                "raw": "..."
            }
        """
        outfits = planning_output.get("outfits", [])
        if approved_outfit_indices is not None:
            outfits = [
                outfits[i] for i in approved_outfit_indices
                if 0 <= i < len(outfits)
            ]

        planning_json = json.dumps(outfits, indent=2)

        description = (
            "You have received the following outfit suggestions from the planning agent:\n\n"
            "{planning_json}\n\n"
            "For each outfit, use the outfit_product_scraper tool on every clothing piece "
            "to fetch up to 5 bestseller product links from Amazon, Flipkart, Myntra, "
            "and Meesho.\n"
            "Research and recommend specific products for {shopping_request}.\n"
            "Compare options by price, quality, and fit with user preferences.\n"
            "Stay within the budget of {budget}."
        ).format(planning_json=planning_json, **inputs)

        t = Task(
            description=description,
            expected_output=(
                "A JSON array of product recommendations. Each entry must have: "
                "outfit_name, and products (list of objects with product_name, "
                "product_url, product_price, product_rating, product_rank)."
            ),
            agent=self.recommendation_agent(),
        )

        single_crew = Crew(
            agents=[self.recommendation_agent()],
            tasks=[t],
            process=Process.sequential,
            verbose=True,
        )

        result = single_crew.kickoff(inputs=inputs)
        raw = str(result)
        parsed = self._parse_recommendation_output(raw)
        return parsed

    def run_visualization(self, outfit_description: str, body_type: str, height: str = "") -> dict:
        """Run only the visualization agent/task.

        Args:
            outfit_description: plain-text description of the outfit items.
            body_type: user's body type, e.g. 'slim', 'curvy', 'athletic'.
            height: user's height, e.g. '5\'6"'.

        Returns:
            {"image_path": "...", "markdown_report": "...", "raw": "..."}
        """
        height_line = f"  - height: \"{height}\"\n" if height else ""
        description = (
            f"Call the outfit_visualizer tool ONCE with:\n"
            f"  - outfit_description: \"{outfit_description}\"\n"
            f"  - body_type: \"{body_type}\"\n"
            f"{height_line}\n"
            "Return the file path or URL returned by the tool."
        )

        t = Task(
            description=description,
            expected_output="The saved image file path or URL returned by the outfit_visualizer tool.",
            agent=self.visualize_agent(),
        )

        single_crew = Crew(
            agents=[self.visualize_agent()],
            tasks=[t],
            process=Process.sequential,
            verbose=True,
        )

        result = single_crew.kickoff()
        raw = str(result)
        parsed = self._parse_visualization_output(raw)
        return parsed

    # ==================================================================
    # Private parsing helpers
    # ==================================================================

    def _extract_json_from_text(self, text: str):
        """Try several strategies to extract JSON from a raw agent response.

        Returns the parsed Python object (list or dict), or None on failure.
        """
        # 1. Strip markdown code fences: ```json ... ``` or ``` ... ```
        fenced = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        candidate = fenced.group(1) if fenced else text

        # 2. Try direct parse of the candidate
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 3. Try to find the outermost JSON array
        array_match = re.search(r'(\[[\s\S]*\])', candidate)
        if array_match:
            try:
                return json.loads(array_match.group(1))
            except json.JSONDecodeError:
                pass

        # 4. Try to find the outermost JSON object
        obj_match = re.search(r'(\{[\s\S]*\})', candidate)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    def _parse_planning_output(self, raw: str) -> dict:
        """Extract outfit list and optional weather data from planning raw output.

        Returns:
            {"outfits": [...], "weather": {}, "raw": raw}
        """
        parsed = self._extract_json_from_text(raw)

        outfits = []
        weather = {}

        if isinstance(parsed, list):
            outfits = parsed
        elif isinstance(parsed, dict):
            # Some models wrap outfits inside {"outfits": [...], "weather": {...}}
            outfits = parsed.get("outfits", parsed.get("outfit_suggestions", []))
            weather = parsed.get("weather", parsed.get("weather_data", {}))
            if not outfits and isinstance(parsed, dict):
                # Treat the whole dict as a single outfit entry
                outfits = [parsed]

        return {"outfits": outfits, "weather": weather, "raw": raw}

    def _parse_recommendation_output(self, raw: str) -> dict:
        """Extract product recommendations from recommendation raw output.

        Returns:
            {"recommendations": [...], "raw": raw}
        """
        parsed = self._extract_json_from_text(raw)

        recommendations = []

        if isinstance(parsed, list):
            recommendations = parsed
        elif isinstance(parsed, dict):
            recommendations = parsed.get(
                "recommendations",
                parsed.get("products", parsed.get("items", [])),
            )
            if not recommendations:
                recommendations = [parsed]

        return {"recommendations": recommendations, "raw": raw}

    def _parse_visualization_output(self, raw: str) -> dict:
        """Extract image path or error from visualization raw output.

        Returns:
            {"image_path": "...", "markdown_report": "...", "raw": raw}
            or {"error": "...", "raw": raw} if the agent reported a failure.
        """
        # Check if agent returned a JSON error object
        try:
            import json as _json
            json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
            if json_match:
                parsed_json = _json.loads(json_match.group())
                if "error" in parsed_json:
                    return {"error": parsed_json["error"], "raw": raw}
                if "image_path" in parsed_json:
                    return {
                        "image_path": parsed_json["image_path"],
                        "markdown_report": raw.strip(),
                        "raw": raw,
                    }
        except Exception:
            pass

        # Fall back to regex extraction
        image_path = ""
        path_patterns = [
            r'!\[.*?\]\(([^)]+\.png)\)',
            r'saved to:\s*([^\n]+\.png)',
            r'(src/shopai/output/[^\s\n]+\.png)',
            r'(/[^\s\n]+\.png)',
        ]
        for pattern in path_patterns:
            match = re.search(pattern, raw)
            if match:
                image_path = match.group(1).strip()
                break

        return {
            "image_path": image_path,
            "markdown_report": raw.strip(),
            "raw": raw,
        }
