from pydantic import BaseModel
from typing import List, Dict, Optional

class Task(BaseModel):
    name: str
    interval_weeks: int = 1   # 1 = jede Woche, 2 = alle zwei Wochen

class CleaningPlan(BaseModel):
    id: str
    name: str
    tasks: List[Task] = []
    interval_weeks: int = 1   # NEU: Wie oft muss der Raum geputzt werden?

class HouseholdCreate(BaseModel):
    name: str
    members: List[str]
    cleaning_plans: List[CleaningPlan] = []
    allocation_mode: str = "rooms"   # "rooms" oder "tasks"

class VetoRequest(BaseModel):
    by_user: str
    accepted_by: List[str] = []