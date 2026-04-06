"""End-to-end test: init → look → solve a puzzle."""
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from agentic_quest.cli import engine, main


class TestEndToEnd:
    def test_full_game_flow(self, tmp_path: Path, presets_dir: Path):
        runner = CliRunner()
        game_dir = tmp_path / "test-adventure"

        # 1. Create a new adventure
        with patch("agentic_quest.cli._find_presets_dir", return_value=presets_dir):
            result = runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "story"])
        assert result.exit_code == 0, result.output
        assert (game_dir / "CLAUDE.md").exists()

        env = {"AQ_GAME_DIR": str(game_dir)}

        # 2. Check status
        result = runner.invoke(engine, ["status"], env=env)
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower()

        # 3. Look around
        result = runner.invoke(engine, ["look"], env=env)
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower() or "Crossroads" in result.output

        # 4. Check paths
        result = runner.invoke(engine, ["paths"], env=env)
        assert result.exit_code == 0

        # 5. View puzzle
        result = runner.invoke(engine, ["puzzle"], env=env)
        assert result.exit_code == 0
        assert "Broken Signpost" in result.output or "signpost" in result.output.lower()

        # 6. Get a hint
        result = runner.invoke(engine, ["hint", "broken_signpost"], env=env)
        assert result.exit_code == 0

        # 7. Solve the puzzle (correctly)
        solution_path = tmp_path / "solution.py"
        solution_path.write_text(
            "def solve(symbols):\n"
            '    order = {"sun": 0, "moon": 1, "star": 2}\n'
            "    return sorted(symbols, key=lambda s: order[s])\n"
        )

        result = runner.invoke(
            engine,
            ["solve", "broken_signpost", "--solution", str(solution_path)],
            env=env,
        )
        assert result.exit_code == 0
        assert "solved" in result.output.lower()

        # 8. Verify puzzle marked solved
        result = runner.invoke(engine, ["puzzle"], env=env)
        assert "SOLVED" in result.output or "solved" in result.output.lower()

        # 9. Check profile updated
        result = runner.invoke(engine, ["profile"], env=env)
        assert result.exit_code == 0
        assert "function_completion" in result.output

        # 10. Verify CLAUDE.md has engine instructions
        claude_md = (game_dir / "CLAUDE.md").read_text()
        assert "engine status" in claude_md
        assert "engine look" in claude_md
        assert "STORY" in claude_md

    def test_wrong_solution_then_correct(self, tmp_path: Path, presets_dir: Path):
        """Test the failure → retry → success flow."""
        runner = CliRunner()
        game_dir = tmp_path / "test-adventure"

        with patch("agentic_quest.cli._find_presets_dir", return_value=presets_dir):
            runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "technical"])

        env = {"AQ_GAME_DIR": str(game_dir)}

        # Wrong solution
        wrong_path = tmp_path / "wrong.py"
        wrong_path.write_text("def solve(symbols):\n    return symbols\n")

        result = runner.invoke(
            engine,
            ["solve", "broken_signpost", "--solution", str(wrong_path)],
            env=env,
        )
        assert "fail" in result.output.lower()

        # Correct solution
        correct_path = tmp_path / "correct.py"
        correct_path.write_text(
            "def solve(symbols):\n"
            '    order = {"sun": 0, "moon": 1, "star": 2}\n'
            "    return sorted(symbols, key=lambda s: order[s])\n"
        )

        result = runner.invoke(
            engine,
            ["solve", "broken_signpost", "--solution", str(correct_path)],
            env=env,
        )
        assert "solved" in result.output.lower()
