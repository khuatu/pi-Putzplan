from pydantic import BaseModel
from typing import List, Dict, Optional

class Task(BaseModel):
    name: str
    interval_weeks: int = 1      # 1 = wöchentlich, 2 = alle zwei Wochen

class CleaningPlan(BaseModel):
    id: str
    name: str
    tasks: List[Task]

class HouseholdCreate(BaseModel):
    name: str
    members: List[str]
    cleaning_plans: List[CleaningPlan]

class VetoRequest(BaseModel):
    by_user: str
    accepted_by: List[str] = []
