import json
import re
import uuid

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from shopai.clarity import score_request
from shopai.conversation_summary import request_context, should_summarize, split_for_fold
from shopai.llm import default_llm, llm_for
from shopai.memory import memory
from shopai.prompts import (
    PLANNING_PROMPT_TEMPLATE,
    PLANNING_SYSTEM_TEMPLATE,
    RECOMMENDATION_SYSTEM_TEMPLATE,
    RECOMMENDATION_PROMPT_TEMPLATE,
    VISUALIZE_SYSTEM_TEMPLATE,
    VISUALIZE_PROMPT_TEMPLATE,
)
from shopai.clarification import ClarificationAssessment, fallback_result, verify_assessment
from shopai.remember import remember
from shopai.tools.clarification_tools import clarification_context_tools
from shopai.tools.user_memory_tools import user_memory_tools
from shopai.tools.outfit_scraper_tool import OutfitScraperTool
from shopai.tools.task_ledger_tools import task_ledger_tools
from shopai.tools.validation_tools import validate_request
from shopai.tools.outfit_visualization_tool import OutfitVisualizationTool
from shopai.tools.weather_tool import WeatherByLocationTool


# The clarifier turns one named gap into one question - small, bounded work
# that would suit a smaller model than the rest of the crew needs.
#
# Empty for now, meaning it shares the crew's default. The gateway this
# project points at only has usable provider keys behind its own "auto"
# routing: naming a model directly - gemma-4-31b-it, qwen3-8b, gpt-5-mini,
# any of them - returns "no candidate model has a configured, usable provider
# key" or an exhausted quota. Set this to a model id once the gateway can
# serve one, and llm_for() will pin it.



def _brief(matched: dict) -> str:
    """What the shopper has told us, verified, as one line for the crew."""
    parts = [f"{category}: {', '.join(words)}" for category, words in matched.items() if words]
    return "; ".join(parts) or "nothing specific"


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
        """Manager of the recommendation crew - delegates, never executes.

        Carries no tools of its own. CrewAI refuses a `manager_agent` that has
        any, because it reserves the manager's toolset for the delegation tools
        it injects. The ledger reaches it on the task instead - see
        `recommendation_crew`.
        """
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

    def clarification_agent(self, run_id: str = "", access_token: str = "") -> Agent:
        """Judges which categories the shopper stated, using read-only context tools.

        Not a manager, so CrewAI lets it hold tools. No delegation: it has no
        one to hand work to.
        """
        return Agent(
            llm=default_llm(),
            config=self.agents_config['clarification_agent'],  # type: ignore[index]
            tools=clarification_context_tools(run_id, access_token),
            allow_delegation=False,
            # Bounded so the fallback fires well inside the app's 120 s read
            # timeout; an unbounded clarifier would outlive the request.
            max_iter=4,
            max_execution_time=60,
            verbose=True,
        )

    def recommendation_crew(self, run_id: str = "") -> Crew:
        """Hierarchical crew: the master routes work to the specialists.

        CrewAI requires the manager to sit outside the agents list, and refuses
        a manager carrying tools. The ledger therefore rides on the master's
        task rather than on the master: at execution time CrewAI resolves
        `task.tools or agent.tools` and then merges the delegation tools into
        whatever that produced, so the master ends up holding both.
        """
        return Crew(
            agents=[
                self.recommendation_agent(),
                self.review_recommendation_agent(),
                self.visualize_agent(),
            ],
            tasks=[
                Task(
                    config=self.tasks_config['master_recommendation_task'],  # type: ignore[index]
                    tools=task_ledger_tools(run_id) if run_id else [],
                ),
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

    def summarizer_agent(self) -> Agent:
        """Folds old turns into a short summary. No tools: it only rewrites text."""
        return Agent(
            llm=default_llm(),
            config=self.agents_config['summarizer_agent'],  # type: ignore[index]
            tools=[],
            allow_delegation=False,
            max_iter=2,
            max_execution_time=60,
        )

    def profile_learner_agent(self, access_token: str, user_text: str) -> Agent:
        """Saves lasting facts. Its update tool is bound to this token and to the
        verbatim words it was shown, so it cannot write for anyone else or cite
        words nobody said."""
        return Agent(
            llm=default_llm(),
            config=self.agents_config['profile_learner_agent'],  # type: ignore[index]
            tools=user_memory_tools(access_token, user_text),
            allow_delegation=False,
            max_iter=6,
            max_execution_time=90,
        )

    def run_summarize(self, previous: str, turns_text: str) -> str:
        """The updated summary, or "" when the model failed (the caller retries later)."""
        try:
            agent = self.summarizer_agent()
            task = Task(config=self.tasks_config['summarize_task'], agent=agent)  # type: ignore[index]
            crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
            return str(crew.kickoff(inputs={
                "previous_summary": previous or "none yet",
                "turns": turns_text,
            })).strip()
        except Exception:
            return ""

    def run_learner(self, user_text: str, access_token: str) -> bool:
        """True when the learner ran to completion (whether or not it saved anything)."""
        try:
            agent = self.profile_learner_agent(access_token, user_text)
            task = Task(config=self.tasks_config['learn_task'], agent=agent)  # type: ignore[index]
            Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff(
                inputs={"turns": user_text}
            )
            return True
        except Exception:
            return False

    def maintain_conversation(self, run_id: str, access_token: str, final: bool = False) -> dict:
        """Fold old turns into the summary, and learn from them, when it is time.

        Time is: the turns since the last summary pass the threshold, or the chat
        has ended (`final`). The learner and Mem0 read the verbatim turns about to
        be folded - never the summary - and the transcript itself is never
        deleted, so a failed step simply retries next time: each marker only
        advances when its own step succeeds. Never raises.
        """
        if not access_token:
            return {"skipped": "guest"}

        convo = memory.conversation
        try:
            row = convo.read_summary(run_id, access_token=access_token)
            fresh = convo.turns_since(run_id, row.get("through_at"), access_token=access_token)
            unseen = convo.turns_since(run_id, row.get("learned_through"), access_token=access_token)

            if final:
                to_fold, recent = fresh, []
            elif should_summarize(fresh):
                to_fold, recent = split_for_fold(fresh)
            else:
                return {"summarized": False, "learned": False}

            recent_ids = {t["id"] for t in recent}
            learn_slice = [t for t in unseen if t["id"] not in recent_ids]

            learned = False
            if learn_slice:
                user_text = "\n".join(t["message"] for t in learn_slice if t["sender"] == "user")
                if user_text.strip():
                    learned = self.run_learner(user_text, access_token)
                    remember(learn_slice, access_token, run_id)
                else:
                    learned = True      # nothing the shopper said, so nothing to read
                if learned:
                    convo.write_summary(
                        run_id, learned_through=learn_slice[-1]["created_at"],
                        access_token=access_token,
                    )

            summarized = False
            if to_fold:
                text = "\n".join(
                    f"{'shopper' if t['sender'] == 'user' else 'stylist'}: {t['message']}"
                    for t in to_fold
                )
                summary = self.run_summarize(row.get("summary", ""), text)
                if summary:
                    convo.write_summary(
                        run_id, summary=summary, through_at=to_fold[-1]["created_at"],
                        access_token=access_token,
                    )
                    summarized = True

            return {"summarized": summarized, "learned": learned}
        except Exception:
            return {"skipped": "error"}

    def run_clarification(
        self, prompt: str, user_text: str, run_id: str = "", access_token: str = ""
    ) -> dict:
        """Is this request plannable, and if not, what is the one question?

        A request the keyword scorer already rates high skips the agent -
        there is nothing to ask. Otherwise the agent judges, and Python
        verifies: see shopai.clarification. Any agent failure falls back to
        the keyword scorer with a templated question.
        """
        keyword = score_request(user_text)
        if keyword["tier"] == "high":
            return {**keyword, "question": "", "source": "keyword"}

        try:
            agent = self.clarification_agent(run_id, access_token)
            task = Task(
                config=self.tasks_config['clarification_task'],  # type: ignore[index]
                agent=agent,
                output_pydantic=ClarificationAssessment,
            )
            crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
            assessment = crew.kickoff(inputs={"shopping_request": prompt}).pydantic
            if assessment is None:
                raise ValueError("the clarifier returned no structured output")
            return verify_assessment(assessment, user_text, keyword=keyword)
        except Exception:
            return fallback_result(keyword)

    def _request_so_far(self, run_id: str, prompt: str, scored_text: str, access_token: str) -> str:
        """The shopper's request as the crew should read it.

        A guest has only this message. A signed-in shopper's request is their
        earlier turns - or, once a conversation was long enough to be summarised,
        the summary followed by the turns since.
        """
        if not access_token:
            return prompt
        try:
            row = memory.conversation.read_summary(run_id, access_token=access_token)
            if row.get("summary"):
                turns = memory.conversation.turns_since(
                    run_id, row.get("through_at"), access_token=access_token
                )
                return request_context(row["summary"], turns)
        except Exception:
            pass        # an expired token degrades to the plain accumulated text
        return " ".join(scored_text.split())

    def run_master_recommendation(
        self, prompt: str, profile: dict | None = None, run_id: str | None = None,
        access_token: str = "",
    ) -> dict:
        """Hand a request to the Recommendation Master crew.

        The request is scored for clarity first, and the tier goes into the
        crew's inputs - the master routes on it: high runs the plan workflow,
        medium and low go to the clarification agent.

        Scoring reads the run's accumulated user turns rather than this one
        message, which is how a vague request climbs low -> medium -> high as
        the user answers.

        Returns:
            {"recommendations": [...], "summary": "...", "raw": "...",
             "run_id": "...", "clarity": {...}}
        """
        run_id = run_id or str(uuid.uuid4())
        profile = profile or {}
        styles = profile.get("styles") or []

        # Written before the read below, not after: scoring must see this
        # message, not just the run's earlier turns.
        self._append_turn(run_id, "user", prompt, access_token)

        scored_text = prompt
        if access_token:
            try:
                scored_text = memory.conversation.user_text(
                    run_id, access_token=access_token
                ) or prompt
            except Exception:
                # A Supabase token is short-lived and the app does not refresh
                # it yet, so an expired one here is routine. Falling back to
                # scoring this message alone loses the run's earlier turns,
                # not the run itself - better than failing the whole request
                # over a transcript read.
                pass
        clarity = self.run_clarification(prompt, scored_text, run_id, access_token)
        if clarity["tier"] != "high":
            question = clarity["question"]
            self._append_turn(run_id, "agent", question, access_token)
            return {
                "recommendations": [],
                "summary": question,
                "raw": question,
                "run_id": run_id,
                "clarity": clarity,
            }

        inputs = {
            "shopping_request": self._request_so_far(run_id, prompt, scored_text, access_token),
            "location": "India",
            "budget": "5000 INR",
            "gender": profile.get("gender") or "female",
            "height": profile.get("height") or "5'6\"",
            "body_type": profile.get("bodyType") or "average",
            "style": ", ".join(styles) or "casual",
            # The master sees which run it is on. Its ledger tools are already
            # bound to this id and take no run_id argument, so this is for the
            # agent's own reference - it cannot be used to write elsewhere.
            "run_id": run_id,
            "request_brief": _brief(clarity["matched"]),
            "clarity_tier": clarity["tier"],
            "clarity_present": ", ".join(clarity["present"]) or "none",
            "clarity_missing": ", ".join(clarity["missing"]) or "none",
            "explicit_request": (
                "yes - they asked to be shown recommendations" if clarity["explicit_request"] else "no"
            ),
            "wants_choice": (
                "yes - they asked you to help them choose" if clarity["wants_choice"] else "no"
            ),
        }

        raw = str(self.recommendation_crew(run_id).kickoff(inputs=inputs))
        parsed = self._parse_recommendation_crew_output(raw)

        # Only carries text when there is text to carry: a real plan's summary
        # is always blank (see _parse_recommendation_crew_output), so nothing
        # gets written for it - there was never a client-facing message to
        # record in that case either.
        self._append_turn(run_id, "agent", parsed.get("summary", ""), access_token)

        return {**parsed, "run_id": run_id, "clarity": clarity}

    def _append_turn(self, run_id: str, sender: str, message: str, access_token: str) -> None:
        """Record one turn in the run's transcript. Best-effort.

        A Supabase access token is short-lived (~1h) and not every caller
        refreshes it yet, so a write failure here is routine, not exceptional -
        it must never cost the caller their plan. Recording the transcript is
        infrastructure for scoring and history, not the thing that was asked for.
        """
        if not access_token or not message:
            return

        try:
            memory.conversation.append(run_id, sender, message, access_token=access_token)
        except Exception:
            pass

    def _parse_recommendation_crew_output(self, raw: str) -> dict:
        """The manager writes prose as often as JSON - keep whichever we get."""
        parsed = self._extract_json_from_text(raw)

        if isinstance(parsed, dict) and isinstance(parsed.get("recommendations"), list):
            return {
                "recommendations": parsed["recommendations"],
                "summary": "",
                "raw": raw,
                "top_pick": str(parsed.get("top_pick") or ""),
            }

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
