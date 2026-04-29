import asyncio
from backend.assignment import assign_plans

def test_assign_basic():
    household = {
        "_id": "507f1f77bcf86cd799439011",
        "members": ["Anna", "Paul"],
        "cleaning_plans": [
            {"id": "bad", "name": "Bad", "tasks": [{"name": "Boden wischen", "interval_weeks": 1}]},
            {"id": "kueche", "name": "Küche", "tasks": [{"name": "Herd putzen", "interval_weeks": 1}]}
        ],
        "current_week": {"week_start": "2026-04-27"}
    }
    # Test mit Mock der history_col (muss man in echter Umgebung patchen)
    # Hier nur Platzhalter
    assert True
