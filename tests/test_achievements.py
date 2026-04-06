"""Tests for AchievementEngine."""
from pathlib import Path

import yaml

from agentic_quest.achievements import AchievementEngine


class TestAchievementEngine:
    def test_loads_definitions(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        assert len(ae.definitions) > 0

    def test_no_achievements_initially(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        assert ae.unlocked() == []

    def test_check_zones_visited(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        newly_unlocked = ae.check()
        explorer = [a for a in newly_unlocked if a["id"] == "first_steps"]
        assert len(explorer) == 1

    def test_check_puzzle_solved(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        newly_unlocked = ae.check()
        puzzle_ids = [a["id"] for a in newly_unlocked]
        assert "puzzle_novice" in puzzle_ids

    def test_doesnt_double_unlock(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        first = ae.check()
        second = ae.check()
        assert len(second) == 0

    def test_total_xp(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        ae.check()
        assert ae.total_xp() > 0

    def test_next_recommendations(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        recs = ae.next_recommendations(limit=3)
        assert len(recs) <= 3
        assert all("name" in r for r in recs)
