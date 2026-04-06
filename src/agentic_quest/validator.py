"""Puzzle validator — runs validate.py against a solution in a subprocess."""
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


_RUNNER_TEMPLATE = """\
import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    solution = load_module("solution", {solution_path!r})
    validator = load_module("validator", {validate_path!r})

    if not hasattr(solution, "solve"):
        print("ERROR: solution.py must define a solve() function", file=sys.stderr)
        sys.exit(1)

    result = validator.validate(solution.solve)
    if result:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL: validator returned falsy", file=sys.stderr)
        sys.exit(1)
except AssertionError as e:
    print(f"FAIL: {{e}}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
"""


@dataclass
class ValidationResult:
    passed: bool
    error: str | None = None
    output: str | None = None


class PuzzleValidator:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def run(self, validate_path: Path, solution_path: Path) -> ValidationResult:
        runner_code = _RUNNER_TEMPLATE.format(
            solution_path=str(solution_path),
            validate_path=str(validate_path),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(runner_code)
            runner_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, runner_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if proc.returncode == 0:
                return ValidationResult(passed=True, output=proc.stdout.strip())
            else:
                return ValidationResult(
                    passed=False,
                    error=proc.stderr.strip() or proc.stdout.strip(),
                )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                error=f"Timeout: solution took longer than {self.timeout}s",
            )
        finally:
            Path(runner_path).unlink(missing_ok=True)
