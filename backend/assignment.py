import random
from typing import Dict, List
from datetime import datetime
from backend.database import history_col

async def assign_plans(household: dict, history_weeks: int = 8) -> Dict[str, List[str]]:
    members = household["members"]
    plans = household["cleaning_plans"]
    current = household.get("current_week", {})
    week_start = current.get("week_start", "")

    # Aktuelle Wochennummer (aus ISO-Kalender) ermitteln
    current_week_num = 0
    if week_start:
        try:
            dt = datetime.strptime(week_start, "%Y-%m-%d")
            iso = dt.isocalendar()
            current_week_num = iso.year * 100 + iso.week
        except:
            pass

    # Sammle alle aktiven Aufgaben-IDs (plan_id|task_index)
    tasks = []
    for plan in plans:
        for idx, task in enumerate(plan["tasks"]):
            interval = task.get("interval_weeks", 1)
            # Offset verhindert, dass alle 2-Wochen-Aufgaben gleichzeitig anfallen
            offset = sum(ord(c) for c in task["name"]) % interval
            if (current_week_num - offset) % interval == 0:
                tid = f"{plan['id']}|{idx}"
                tasks.append(tid)

    if not tasks:
        return {m: [] for m in members}

    # Historie der letzten Wochen laden
    pipeline = [
        {"$match": {"household_id": household["_id"]}},
        {"$sort": {"week_start": -1}},
        {"$limit": history_weeks * len(members)}
    ]
    recent = await history_col.aggregate(pipeline).to_list(None)

    # Zähler: wie oft hatte Nutzer diese Aufgabe?
    counts = {m: {t: 0 for t in tasks} for m in members}
    for entry in recent:
        u = entry["user"]
        t = entry.get("task_id")
        if u in counts and t in counts[u]:
            counts[u][t] += 1

    # Gewichte: 1 / (count + 1)
    weights = {}
    for t in tasks:
        weights[t] = []
        for m in members:
            weights[t].append(1.0 / (counts[m][t] + 1))

    # Gleichmäßige Verteilung
    max_per = -(-len(tasks) // len(members))  # ceil division
    assignments = {m: [] for m in members}
    remaining = list(tasks)
    assigned = {m: 0 for m in members}

    while remaining:
        task = random.choice(remaining)
        candidates = [m for m in members if assigned[m] < max_per]
        if not candidates:
            break
        cand_weights = [weights[task][members.index(m)] for m in candidates]
        chosen = random.choices(candidates, weights=cand_weights, k=1)[0]
        assignments[chosen].append(task)
        assigned[chosen] += 1
        remaining.remove(task)

    return assignments