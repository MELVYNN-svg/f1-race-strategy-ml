"""Les emplacements vides du calendrier ne sont pas des sessions."""

from unittest.mock import Mock

import pandas as pd

from f1_project.pipelines.data_ingestion import nodes


def test_ingestion_skips_placeholder_sessions(monkeypatch):
    monkeypatch.setattr(nodes, "configure_cache", lambda: None)
    monkeypatch.setattr(nodes, "save_table", Mock())
    load_session = Mock(side_effect=AssertionError("Aucune session a telecharger"))
    monkeypatch.setattr(nodes.fastf1, "get_testing_session", load_session)
    schedule = pd.DataFrame(
        [
            {
                "RoundNumber": 0,
                "EventName": "Testing",
                "EventFormat": "testing",
                "Session1": "None",
                "Session2": "",
                "Session3": None,
                "Session4": float("nan"),
                "Session5": "<NA>",
            }
        ]
    )
    assert nodes.download_all(schedule, 2025).empty
    load_session.assert_not_called()
