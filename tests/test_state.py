"""Tests for GameState."""
from pathlib import Path

import yaml

from agentic_quest.state import GameState


class TestGameStateLoad:
    def test_loads_player_state(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        assert gs.player["name"] == "Testplayer"
        assert gs.player["location"] == "crossroads"

    def test_loads_world_meta(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        assert gs.meta["seed"] == 42
        assert gs.meta["preset"] == "fantasy"

    def test_raises_on_missing_dir(self, tmp_path: Path):
        import pytest
        with pytest.raises(FileNotFoundError):
            GameState(tmp_path / "nonexistent")


class TestGameStateZones:
    def test_reads_zone(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        zone = gs.get_zone("crossroads")
        assert zone["name"] == "The Crossroads"
        assert "dark_forest" in zone["connections"]

    def test_reads_zone_narrative(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        narrative = gs.get_zone_narrative("crossroads")
        assert "crossroads" in narrative.lower()

    def test_lists_paths(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        paths = gs.get_paths("crossroads")
        assert len(paths) == 2
        assert any(p["name"] == "Dark Forest" for p in paths)

    def test_returns_none_for_missing_zone(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        assert gs.get_zone("nonexistent") is None


class TestGameStatePlayerMutation:
    def test_move_player(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.move_player("dark_forest")
        assert gs.player["location"] == "dark_forest"
        reloaded = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        assert reloaded["location"] == "dark_forest"

    def test_add_to_inventory(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.add_to_inventory("compass_of_seeking")
        assert "compass_of_seeking" in gs.player["inventory"]
        reloaded = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        assert "compass_of_seeking" in reloaded["inventory"]

    def test_add_companion(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.add_companion("scholar")
        assert "scholar" in gs.player["companions"]


class TestGameStatePuzzles:
    def test_get_puzzle(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        puzzle = gs.get_puzzle("crossroads", "broken_signpost")
        assert puzzle["name"] == "The Broken Signpost"
        assert puzzle["type"] == "function_completion"

    def test_get_puzzle_hint(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        hint = gs.get_puzzle_hint("crossroads", "broken_signpost", hint_index=0)
        assert "merchant" in hint.lower()

    def test_mark_puzzle_solved(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.mark_puzzle_solved("crossroads", "broken_signpost")
        puzzle = gs.get_puzzle("crossroads", "broken_signpost")
        assert puzzle.get("solved") is True


class TestNpcEvents:
    def test_record_event(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Sold a compass to the player")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc.get("events", [])) == 1
        assert npc["events"][0]["description"] == "Sold a compass to the player"
        assert "zone" in npc["events"][0]
        assert "move_number" in npc["events"][0]

    def test_record_multiple_events(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Greeted the player")
        gs.record_npc_event("crossroads", "old_merchant", "Gave a hint about the signpost")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc["events"]) == 2

    def test_get_npc(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        npc = gs.get_npc("crossroads", "old_merchant")
        assert npc["name"] == "Old Merchant"
        assert "dialogue" in npc

    def test_get_npc_missing(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        assert gs.get_npc("crossroads", "nobody") is None

    def test_get_npc_events_filtered_by_zone(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Saw the player solve the puzzle", zone="crossroads")
        gs.record_npc_event("crossroads", "old_merchant", "Heard a distant rumble", zone="dark_forest")
        events = gs.get_npc_events_at("crossroads", "old_merchant", perspective_zone="crossroads")
        assert len(events) == 1
        assert events[0]["description"] == "Saw the player solve the puzzle"

    def test_companion_sees_all_events(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Event in crossroads", zone="crossroads")
        gs.record_npc_event("crossroads", "old_merchant", "Event in forest", zone="dark_forest")
        events = gs.get_npc_events_at("crossroads", "old_merchant", perspective_zone=None)
        assert len(events) == 2

    def test_events_capped_at_max(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        for i in range(15):
            gs.record_npc_event("crossroads", "old_merchant", f"Event {i}")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc["events"]) == 10
