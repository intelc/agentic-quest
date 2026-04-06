"""Tests for CLI commands."""
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from agentic_quest.cli import _sanitize_zone_id, engine, main


class TestSanitizeZoneId:
    def test_simple_name(self):
        assert _sanitize_zone_id("Dark Forest") == "dark_forest"

    def test_strips_special_chars(self):
        result = _sanitize_zone_id("The Sunfire Peaks: A Rugged Mountain")
        assert ":" not in result
        assert result.startswith("the_sunfire_peaks")

    def test_truncates_to_three_words(self):
        assert _sanitize_zone_id("the very long zone name here") == "the_very_long"

    def test_handles_colons_and_punctuation(self):
        result = _sanitize_zone_id("Moonwell Grove: A mystical glade")
        assert ":" not in result

    def test_chinese_characters_preserved(self):
        result = _sanitize_zone_id("城南商业街")
        assert len(result) > 0
        assert "城南" in result

    def test_mixed_chinese_english(self):
        result = _sanitize_zone_id("姜宁的公寓 Jiang Ning Apartment")
        assert len(result) > 0

    def test_empty_fallback(self):
        result = _sanitize_zone_id("!@#$%")
        assert len(result) > 0  # should produce a fallback


class TestLifesimNew:
    def test_creates_adventure_directory(self, tmp_path: Path, presets_dir: Path):
        runner = CliRunner()
        game_dir = tmp_path / "my-adventure"
        with patch("agentic_quest.cli._find_presets_dir", return_value=presets_dir):
            result = runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "story"])
        assert result.exit_code == 0, result.output
        assert game_dir.exists()
        assert (game_dir / "CLAUDE.md").exists()


class TestEngineStatus:
    def test_shows_player_location(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["status"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower()
        assert "Testplayer" in result.output

    def test_shows_companions(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["status"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert "scout" in result.output.lower()


class TestEngineLook:
    def test_shows_zone_narrative(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["look"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower()


class TestEnginePaths:
    def test_shows_available_paths(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["paths"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "dark_forest" in result.output.lower() or "Dark Forest" in result.output


class TestEngineMove:
    def test_move_to_existing_zone(self, tmp_game_dir: Path, sample_zone_dir: Path):
        dark_forest = tmp_game_dir / "world" / "dark_forest"
        dark_forest.mkdir()
        (dark_forest / "zone.yaml").write_text(yaml.dump({
            "name": "Dark Forest",
            "description": "A dark forest.",
            "connections": {"crossroads": {"name": "Crossroads", "status": "explored"}},
            "npcs": [],
            "puzzles": [],
        }))
        (dark_forest / "narrative.md").write_text("The trees close in around you.\n")

        runner = CliRunner()
        result = runner.invoke(engine, ["move", "dark_forest"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0

        player = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        assert player["location"] == "dark_forest"


class TestEnginePuzzle:
    def test_shows_puzzle_info(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["puzzle"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "Broken Signpost" in result.output or "broken_signpost" in result.output


class TestEngineSolve:
    def test_correct_solution(self, tmp_game_dir: Path, sample_zone_dir: Path):
        solution_path = tmp_game_dir / "solution.py"
        solution_path.write_text(
            "def solve(symbols):\n"
            '    order = {"sun": 0, "moon": 1, "star": 2}\n'
            "    return sorted(symbols, key=lambda s: order[s])\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["solve", "broken_signpost", "--solution", str(solution_path)],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "pass" in result.output.lower() or "solved" in result.output.lower()

    def test_wrong_solution(self, tmp_game_dir: Path, sample_zone_dir: Path):
        solution_path = tmp_game_dir / "solution.py"
        solution_path.write_text("def solve(symbols):\n    return symbols\n")
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["solve", "broken_signpost", "--solution", str(solution_path)],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        assert "fail" in result.output.lower() or "error" in result.output.lower()


class TestEngineHint:
    def test_shows_hint(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["hint", "broken_signpost"],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "merchant" in result.output.lower() or "sun" in result.output.lower()


class TestEngineInventory:
    def test_shows_empty_inventory(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["inventory"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "no items" in result.output.lower()


class TestEngineCompanions:
    def test_lists_companions(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["companions"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "scout" in result.output.lower()


class TestEngineProfile:
    def test_shows_profile(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["profile"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "difficulty" in result.output.lower()


class TestEngineContext:
    def test_returns_aggregated_state(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["context"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "Testplayer" in result.output
        assert "crossroads" in result.output.lower()
        assert "signpost" in result.output.lower() or "merchant" in result.output.lower()
        assert "dark_forest" in result.output.lower() or "Dark Forest" in result.output
        assert "Broken Signpost" in result.output or "broken_signpost" in result.output


class TestEngineRecordEvent:
    def test_records_npc_event(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["record-event", "old_merchant", "Sold a compass"],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "recorded" in result.output.lower()


class TestEngineSchedule:
    def test_schedules_consequence(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["schedule", "A stranger arrives", "--after", "3"],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "scheduled" in result.output.lower()


class TestEngineConsequences:
    def test_shows_pending(self, tmp_game_dir: Path):
        runner = CliRunner()
        runner.invoke(
            engine,
            ["schedule", "Storm coming", "--after", "2"],
            env={"AQ_GAME_DIR": str(tmp_game_dir)},
        )
        result = runner.invoke(engine, ["consequences"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "Storm coming" in result.output


class TestEngineAchievements:
    def test_shows_achievements(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["achievements"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0

    def test_check_achievements(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        import yaml
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        result = runner.invoke(engine, ["check-achievements"], env={"AQ_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "First Steps" in result.output
