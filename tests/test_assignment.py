# tests/test_assignment.py
import pytest
from backend.assignment import assign_plans
from unittest.mock import AsyncMock, patch

@pytest.fixture
def sample_household():
    return {
        "_id": "507f1f77bcf86cd799439011",
        "members": ["Anna", "Paul"],
        "cleaning_plans": [
            {
                "id": "bad",
                "name": "Bad",
                "tasks": [
                    {"name": "Waschbecken", "interval_weeks": 1},
                    {"name": "Boden wischen", "interval_weeks": 2}
                ]
            },
            {
                "id": "kueche",
                "name": "Küche",
                "tasks": [
                    {"name": "Herd", "interval_weeks": 1},
                    {"name": "Boden wischen", "interval_weeks": 2}
                ]
            }
        ],
        "current_week": {"week_start": "2026-04-27"}  # Montag, ISO-Woche 18
    }

@pytest.mark.asyncio
async def test_assign_plans_basic(sample_household):
    # Mock die history_col.aggregate, um leere Historie zu simulieren
    with patch("backend.assignment.history_col") as mock_col:
        mock_agg = AsyncMock()
        mock_agg.to_list.return_value = []
        mock_col.aggregate.return_value = mock_agg
        assignments = await assign_plans(sample_household, history_weeks=0)
        # Jeder sollte mind. eine Aufgabe haben, wenn aktive Aufgaben existieren
        assert len(assignments["Anna"]) > 0
        assert len(assignments["Paul"]) > 0
        # Zusammen sollen alle aktiven Aufgaben abgedeckt sein
        all_tasks = assignments["Anna"] + assignments["Paul"]
        assert "bad|0" in all_tasks or "kueche|0" in all_tasks