import os, yaml, pandas as pd
from crewai import Agent, Task, Crew
from src.helper import load_env
from src.models.plan import ProjectPlan

def load_yaml(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def build_crew():
    agents_cfg = load_yaml("config/agents.yaml")
    tasks_cfg  = load_yaml("config/tasks.yaml")

    # Agents
    project_planning_agent   = Agent(config=agents_cfg['project_planning_agent'])
    estimation_agent         = Agent(config=agents_cfg['estimation_agent'])
    resource_allocation_agent= Agent(config=agents_cfg['resource_allocation_agent'])

    # Tasks
    task_breakdown = Task(config=tasks_cfg['task_breakdown'], agent=project_planning_agent)
    time_estimation= Task(config=tasks_cfg['time_resource_estimation'], agent=estimation_agent)
    allocation     = Task(config=tasks_cfg['resource_allocation'], agent=resource_allocation_agent,
                          output_pydantic=ProjectPlan)

    crew = Crew(
        agents=[project_planning_agent, estimation_agent, resource_allocation_agent],
        tasks=[task_breakdown, time_estimation, allocation],
        verbose=True
    )
    return crew

def run_pipeline(inputs: dict):
    load_env()
    os.environ.setdefault("OPENAI_MODEL_NAME", "gpt-4o-mini")
    crew = build_crew()
    result = crew.kickoff(inputs=inputs)

    # coûts & métriques
    costs = 0.150 * (crew.usage_metrics.prompt_tokens + crew.usage_metrics.completion_tokens) / 1_000_000
    print(f"[COUT ESTIME] ${costs:.4f}")
    df_usage = pd.DataFrame([crew.usage_metrics.dict()])
    print(df_usage)

    # sorties structurées
    plan = result.pydantic.dict()
    pd.DataFrame(plan["tasks"]).to_csv("outputs/tables/tasks.csv", index=False)
    pd.DataFrame(plan["milestones"]).to_csv("outputs/tables/milestones.csv", index=False)
    print("[OK] Exports -> outputs/tables/")

if __name__ == "__main__":
    demo_inputs = {
        "project_type": "Site web",
        "project_objectives": "Créer un site vitrine",
        "industry": "Technologie",
        "team_members": "- John (PM)\n- Jane (Dev)\n- Bob (Design)\n- Alice (QA)\n- Tom (QA)",
        "project_requirements": "- Responsive\n- UI moderne\n- Nav claire\n- Pages: A propos, Services, Contact\n- Blog\n- SEO\n- Social\n- Témoignages"
    }
    run_pipeline(demo_inputs)
