from typing import List
from pydantic import BaseModel, Field

class TaskEstimate(BaseModel):
    task_name: str = Field(..., description="Nom de la tâche")
    estimated_time_hours: float = Field(..., description="Temps estimé (heures)")
    required_resources: List[str] = Field(..., description="Ressources/personnes requises")

class Milestone(BaseModel):
    milestone_name: str = Field(..., description="Nom du jalon")
    tasks: List[str] = Field(..., description="Tâches associées")

class ProjectPlan(BaseModel):
    tasks: List[TaskEstimate] = Field(..., description="Tâches avec estimations")
    milestones: List[Milestone] = Field(..., description="Jalons du projet")
