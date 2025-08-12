from __future__ import annotations
from crewai import Crew
from loguru import logger

def build_crew(agents, tasks):
    (agent_commercial, agent_chef_commercial) = agents
    (profilage_prospect, campagne_personnalisee) = tasks

    crew = Crew(
        agents=[agent_commercial, agent_chef_commercial],
        tasks=[profilage_prospect, campagne_personnalisee],
        verbose=True,
        memory=True
    )
    return crew

def run_workflow(crew, inputs: dict):
    logger.info(f"Kickoff with inputs: {inputs}")
    result = crew.kickoff(inputs=inputs)
    return result
