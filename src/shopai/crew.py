from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from shopai.prompts import (
    PLANNING_PROMPT_TEMPLATE,
    PLANNING_SYSTEM_TEMPLATE,
    RECOMMENDATION_SYSTEM_TEMPLATE,
    RECOMMENDATION_PROMPT_TEMPLATE,
    VISUALIZE_SYSTEM_TEMPLATE,
    VISUALIZE_PROMPT_TEMPLATE,
)
from shopai.tools.outfit_scraper_tool import OutfitScraperTool
from shopai.tools.outfit_visualization_tool import OutfitVisualizationTool
from shopai.tools.weather_tool import WeatherByLocationTool


@CrewBase
class Shopai():
    """Shopai crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def planning_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['planning_agent'], # type: ignore[index]
            tools=[WeatherByLocationTool()],
            system_template=PLANNING_SYSTEM_TEMPLATE,
            prompt_template=PLANNING_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    @agent
    def recommendation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['recommendation_agent'], # type: ignore[index]
            tools=[OutfitScraperTool()],
            system_template=RECOMMENDATION_SYSTEM_TEMPLATE,
            prompt_template=RECOMMENDATION_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    @task
    def planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['planning_task'], # type: ignore[index]
        )

    @task
    def recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config['recommendation_task'], # type: ignore[index]
            context=[self.planning_task()],
        )
    @agent
    def visualize_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['visualize_agent'], # type: ignore[index]
            tools=[OutfitVisualizationTool()],
            system_template=VISUALIZE_SYSTEM_TEMPLATE,
            prompt_template=VISUALIZE_PROMPT_TEMPLATE,
            use_system_prompt=True,
            verbose=True
        )

    @task
    def visualize_task(self) -> Task:
        return Task(
            config=self.tasks_config['visualize_task'], # type: ignore[index]
            context=[self.planning_task(), self.recommendation_task()],
            output_file='src/shopai/output/shopping_guide.md'
        )




    @crew
    def crew(self) -> Crew:
        """Creates the Shopai crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
