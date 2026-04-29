# backend/assignment.py
import random
from typing import Dict, List
from datetime import datetime
from backend.database import history_col

async def assign_plans(household: dict, history_weeks: int = 8) -> Dict[str, List[str]]:
    members = household["members"]
    plans = household.get("cleaning_plans", [])
    allocation_mode = household.get("allocation_mode", "rooms")  # Standard: Räume
    current_week = household.get("current_week", {})
    week_start = current_week.get("week_start", "")

    # Aktuelle Wochennummer berechnen (wie gehabt)
    current_week_num = 0
    if week_start:
        try:
            dt = datetime.strptime(week_start, "%Y-%m-%d")
            iso = dt.isocalendar()
            current_week_num = iso.year * 100 + iso.week
        except:
            pass

    # --- Modus: Aufgaben verteilen (altes Verhalten) ---
    if allocation_mode == "tasks":
        tasks = []
        for plan in plans:
            for idx, task in enumerate(plan.get("tasks", [])):
                interval = task.get("interval_weeks", 1)
                offset = sum(ord(c) for c in task["name"]) % interval
                if (current_week_num - offset) % interval == 0:
                    tid = f"{plan['id']}|{idx}"
                    tasks.append(tid)
        if not tasks:
            return {m: [] for m in members}

        # Historie für Aufgaben laden
        pipeline = [
            {"$match": {"household_id": household["_id"]}},
            {"$sort": {"week_start": -1}},
            {"$limit": history_weeks * len(members)}
        ]
        recent = await history_col.aggregate(pipeline).to_list(None)

        counts = {m: {t: 0 for t in tasks} for m in members}
        for entry in recent:
            u = entry["user"]
            t = entry.get("task_id")
            if u in counts and t in counts[u]:
                counts[u][t] += 1

        weights = {t: [1.0 / (counts[m].get(t, 0) + 1) for m in members] for t in tasks}
        max_per = -(-len(tasks) // len(members))
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

    # --- Modus: Räume verteilen (NEU) ---
    else:
        # Sammle alle Räume, die diese Woche aktiv sind
        active_plans = []
        for plan in plans:
            interval = plan.get("interval_weeks", 1)
            # Offset für Raum berechnen (wie bei Aufgaben, aber auf Raumname)
            offset = sum(ord(c) for c in plan["name"]) % interval
            if (current_week_num - offset) % interval == 0:
                active_plans.append(plan["id"])

        if not active_plans:
            return {m: [] for m in members}

        # Historie für Räume laden (statt tasks)
        pipeline = [
            {"$match": {"household_id": household["_id"], "completed": True}},
            {"$sort": {"week_start": -1}},
            {"$limit": history_weeks * len(members)}
        ]
        recent = await history_col.aggregate(pipeline).to_list(None)

        counts = {m: {p: 0 for p in active_plans} for m in members}
        for entry in recent:
            u = entry["user"]
            p = entry.get("plan_id")
            if u in counts and p in counts[u]:
                counts[u][p] += 1

        weights = {p: [1.0 / (counts[m].get(p, 0) + 1) for m in members] for p in active_plans}
        max_per = -(-len(active_plans) // len(members))
        assignments = {m: [] for m in members}
        remaining = list(active_plans)
        assigned = {m: 0 for m in members}

        while remaining:
            plan_id = random.choice(remaining)
            candidates = [m for m in members if assigned[m] < max_per]
            if not candidates:
                break
            cand_weights = [weights[plan_id][members.index(m)] for m in candidates]
            chosen = random.choices(candidates, weights=cand_weights, k=1)[0]
            assignments[chosen].append(plan_id)
            assigned[chosen] += 1
            remaining.remove(plan_id)
        return assignments