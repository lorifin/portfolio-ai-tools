# L1 : Projet automatisé : Planification, Estimation et Allocation

# ⏳ Note (Démarrage du kernel) : ce notebook met ~30 secondes à être prêt.

# ====== Imports initiaux ======
import warnings
warnings.filterwarnings('ignore')
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from helper import load_env

# Chargement des variables d'environnement
from helper import load_env
load_env()

import os
import yaml
from crewai import Agent, Task, Crew

# 💻 Astuce : pour ouvrir requirements.txt et helper.py :
# Menu "File" du notebook -> "Open". Voir aussi "Appendix - Tips and Help".

# ====== Sélection du modèle OpenAI ======
os.environ['OPENAI_MODEL_NAME'] = 'gpt-4o-mini'


# ====== Chargement des fichiers YAML (Agents & Tasks) ======
# Chemins vers les configurations YAML
files = {
    'agents': 'config/agents.yaml',
    'tasks':  'config/tasks.yaml'
}

# Lecture sécurisée des YAML
configs = {}
for config_type, file_path in files.items():
    with open(file_path, 'r') as f:
        configs[config_type] = yaml.safe_load(f)

# Références pratiques
agents_config = configs['agents']
tasks_config  = configs['tasks']


# ====== Modèles Pydantic pour la sortie structurée ======
from typing import List
from pydantic import BaseModel, Field

class TaskEstimate(BaseModel):
    task_name: str = Field(..., description="Nom de la tâche")
    estimated_time_hours: float = Field(..., description="Temps estimé (heures)")
    required_resources: List[str] = Field(..., description="Ressources/personnes requises")

class Milestone(BaseModel):
    milestone_name: str = Field(..., description="Nom du jalon")
    tasks: List[str] = Field(..., description="Liste d'ID/nom de tâches associées")

class ProjectPlan(BaseModel):
    tasks: List[TaskEstimate] = Field(..., description="Liste des tâches estimées")
    milestones: List[Milestone] = Field(..., description="Liste des jalons du projet")


# ====== Création des Agents et Tâches CrewAI ======
# Agents
project_planning_agent = Agent(config=agents_config['project_planning_agent'])
estimation_agent       = Agent(config=agents_config['estimation_agent'])
resource_allocation_agent = Agent(config=agents_config['resource_allocation_agent'])

# Tâches (chaque Task est associé à un Agent)
task_breakdown = Task(
    config=tasks_config['task_breakdown'],
    agent=project_planning_agent
)

time_resource_estimation = Task(
    config=tasks_config['time_resource_estimation'],
    agent=estimation_agent
)

resource_allocation = Task(
    config=tasks_config['resource_allocation'],
    agent=resource_allocation_agent,
    output_pydantic=ProjectPlan  # Sortie structurée attendue
)

# Crew (équipe multi-agents)
crew = Crew(
    agents=[
        project_planning_agent,
        estimation_agent,
        resource_allocation_agent
    ],
    tasks=[
        task_breakdown,
        time_resource_estimation,
        resource_allocation
    ],
    verbose=True
)
# (Vous pouvez ignorer un éventuel warning OpenTelemetry sur le TracerProvider)


# ====== Données d'entrée du projet ======
from IPython.display import display, Markdown

project = 'Site web'
industry = 'Technologie'
project_objectives = "Créer un site vitrine pour une petite entreprise"
team_members = """
- John Doe (Chef de projet)
- Jane Doe (Ingénieure logicielle)
- Bob Smith (Designer)
- Alice Johnson (QA Engineer)
- Tom Brown (QA Engineer)
"""
project_requirements = """
- Créer un design responsive (desktop & mobile)
- UI moderne, visuellement soignée, look épuré
- Navigation claire avec menu intuitif
- Page “À propos” (histoire & valeurs)
- Page “Services” (offres + descriptions)
- Page “Contact” (formulaire + carte intégrée)
- Section Blog (actus & mises à jour)
- Performances élevées + SEO de base
- Liens & partages réseaux sociaux
- Section Témoignages (preuve sociale)
"""

# Affichage lisible dans Jupyter
formatted_output = f"""
**Type de projet :** {project}

**Objectifs :** {project_objectives}

**Secteur :** {industry}

**Membres de l'équipe :**
{team_members}
**Exigences du projet :**
{project_requirements}
"""
display(Markdown(formatted_output))


# ====== Lancement de la Crew ======
inputs = {
    'project_type': project,
    'project_objectives': project_objectives,
    'industry': industry,
    'team_members': team_members,
    'project_requirements': project_requirements
}

# Exécution pipeline multi-agents
result = crew.kickoff(inputs=inputs)


# ====== Coûts & métriques d'usage (exemple de calcul) ======
import pandas as pd

costs = 0.150 * (crew.usage_metrics.prompt_tokens + crew.usage_metrics.completion_tokens) / 1_000_000
print(f"Coût estimé par exécution : ${costs:.4f}")

df_usage_metrics = pd.DataFrame([crew.usage_metrics.dict()])
df_usage_metrics  # affichage dans le notebook


# ====== Récupération de la sortie structurée (Pydantic) ======
# La tâche d'allocation de ressources renvoie un ProjectPlan
plan_dict = result.pydantic.dict()
plan_dict  # inspection brute

# Confort de lecture : tableaux des tâches et jalons
df_tasks = pd.DataFrame(plan_dict['tasks'])
df_tasks

df_milestones = pd.DataFrame(plan_dict['milestones'])
df_milestones

from pprint import pprint
import pandas as pd
import os

# Afficher en console
pprint(result.pydantic.dict())

import os, csv, json


os.makedirs("outputs/tables", exist_ok=True)
plan = result.pydantic.dict()

# ---- Tasks.csv (propre, UTF-8) ----
df_tasks = pd.DataFrame(plan["tasks"])
df_tasks.to_csv("outputs/tables/tasks.csv", index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

# ---- Milestones.csv : on *joint* la liste de tâches pour éviter les crochets dans le CSV ----
df_milestones = pd.DataFrame(plan["milestones"]).copy()
df_milestones["tasks"] = df_milestones["tasks"].apply(lambda xs: "; ".join(xs))
df_milestones.to_csv("outputs/tables/milestones.csv", index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

# ---- (Optionnel) JSON complet pour réutilisation API/Notion/Jira ----
with open("outputs/tables/project_plan.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

print("[OK] Écrit : outputs/tables/tasks.csv, milestones.csv, project_plan.json")
