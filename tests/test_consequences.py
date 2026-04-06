"""Tests for ConsequenceManager."""
from pathlib import Path

from agentic_quest.consequences import ConsequenceManager


class TestConsequenceManager:
    def test_loads_empty(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        assert cm.pending() == []

    def test_schedule_consequence(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("A stranger arrives at the crossroads", trigger_after_moves=3)
        assert len(cm.pending()) == 1
        assert cm.pending()[0]["description"] == "A stranger arrives at the crossroads"
        assert cm.pending()[0]["moves_remaining"] == 3

    def test_schedule_with_zone(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Bridge collapses", trigger_after_moves=2, zone="river_valley")
        assert cm.pending()[0]["zone"] == "river_valley"

    def test_schedule_with_type(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("New path opens", trigger_after_moves=1, event_type="path_opens")
        assert cm.pending()[0]["type"] == "path_opens"

    def test_tick_decrements_moves(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Something happens", trigger_after_moves=3)
        fired = cm.tick()
        assert fired == []
        assert cm.pending()[0]["moves_remaining"] == 2

    def test_tick_fires_at_zero(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Something happens", trigger_after_moves=1)
        fired = cm.tick()
        assert len(fired) == 1
        assert fired[0]["description"] == "Something happens"
        assert cm.pending() == []

    def test_tick_fires_multiple(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("First", trigger_after_moves=1)
        cm.schedule("Second", trigger_after_moves=1)
        cm.schedule("Third", trigger_after_moves=3)
        fired = cm.tick()
        assert len(fired) == 2
        assert len(cm.pending()) == 1

    def test_persists_to_disk(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Persistent event", trigger_after_moves=5)
        cm2 = ConsequenceManager(tmp_game_dir)
        assert len(cm2.pending()) == 1
        assert cm2.pending()[0]["description"] == "Persistent event"

    def test_fired_events_saved_to_history(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Past event", trigger_after_moves=1)
        cm.tick()
        assert len(cm.history()) == 1
        assert cm.history()[0]["description"] == "Past event"
