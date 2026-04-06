"""Tests for PuzzleValidator."""
from pathlib import Path
from textwrap import dedent

from agentic_quest.validator import PuzzleValidator, ValidationResult


class TestPuzzleValidator:
    def test_correct_solution_passes(self, tmp_path: Path):
        validate_py = tmp_path / "validate.py"
        validate_py.write_text(dedent("""\
            def validate(solution_fn):
                assert solution_fn([3, 1, 2]) == [1, 2, 3]
                return True
        """))
        solution_py = tmp_path / "solution.py"
        solution_py.write_text(dedent("""\
            def solve(items):
                return sorted(items)
        """))
        validator = PuzzleValidator()
        result = validator.run(validate_py, solution_py)
        assert result.passed is True
        assert result.error is None

    def test_wrong_solution_fails(self, tmp_path: Path):
        validate_py = tmp_path / "validate.py"
        validate_py.write_text(dedent("""\
            def validate(solution_fn):
                assert solution_fn([3, 1, 2]) == [1, 2, 3]
                return True
        """))
        solution_py = tmp_path / "solution.py"
        solution_py.write_text(dedent("""\
            def solve(items):
                return items
        """))
        validator = PuzzleValidator()
        result = validator.run(validate_py, solution_py)
        assert result.passed is False
        assert result.error is not None

    def test_syntax_error_in_solution(self, tmp_path: Path):
        validate_py = tmp_path / "validate.py"
        validate_py.write_text(dedent("""\
            def validate(solution_fn):
                assert solution_fn(1) == 2
                return True
        """))
        solution_py = tmp_path / "solution.py"
        solution_py.write_text("def solve(x)\n    return x")  # missing colon
        validator = PuzzleValidator()
        result = validator.run(validate_py, solution_py)
        assert result.passed is False
        assert "SyntaxError" in result.error

    def test_timeout_on_infinite_loop(self, tmp_path: Path):
        validate_py = tmp_path / "validate.py"
        validate_py.write_text(dedent("""\
            def validate(solution_fn):
                solution_fn(1)
                return True
        """))
        solution_py = tmp_path / "solution.py"
        solution_py.write_text(dedent("""\
            def solve(x):
                while True:
                    pass
        """))
        validator = PuzzleValidator(timeout=2)
        result = validator.run(validate_py, solution_py)
        assert result.passed is False
        assert "timeout" in result.error.lower()

    def test_crossroads_puzzle(self, sample_zone_dir: Path):
        """Test with the actual starter puzzle from the preset."""
        validate_py = sample_zone_dir / "broken_signpost" / "validate.py"
        solution_py = sample_zone_dir.parent / "solution.py"
        solution_py.write_text(dedent("""\
            def solve(symbols):
                order = {"sun": 0, "moon": 1, "star": 2}
                return sorted(symbols, key=lambda s: order[s])
        """))
        validator = PuzzleValidator()
        result = validator.run(validate_py, solution_py)
        assert result.passed is True
