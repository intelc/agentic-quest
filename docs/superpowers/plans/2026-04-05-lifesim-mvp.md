# LifeSim MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable LLM-powered text RPG engine where users explore a procedurally generated fantasy world, solve narrative-framed puzzles backed by Python validators, and dispatch companion subagents — all from Claude Code.

**Architecture:** Python CLI engine (`engine` command) manages game state as YAML/Markdown files. Claude Code reads a generated CLAUDE.md and acts as narrator, calling engine commands via Bash. Terrain generation uses the Anthropic API to create zones/puzzles from prompt templates. Puzzles use Python validator functions; solutions are submitted as Python files.

**Tech Stack:** Python 3.11+, Click (CLI framework), PyYAML, Anthropic Python SDK, Jinja2 (prompt templates), pytest

---

## File Structure

```
lifesim/
├── pyproject.toml                      # package config, [project.scripts] lifesim = lifesim.cli:main
├── src/
│   └── lifesim/
│       ├── __init__.py
│       ├── cli.py                      # Click CLI entry point — all engine commands
│       ├── state.py                    # GameState class — reads/writes player/, world/ YAML files
│       ├── generator.py               # ZoneGenerator — calls Anthropic API with prompt templates
│       ├── validator.py               # PuzzleValidator — runs validate.py in subprocess, returns result
│       ├── profile.py                 # PlayerProfile — tracks behavior signals, updates profile.yaml
│       └── init.py                    # GameInitializer — scaffolds new game from preset
├── presets/
│   └── fantasy/
│       ├── preset.yaml                # metadata: name, description, seed defaults
│       ├��─ voice.md                   # narrative style guide for Claude
│       ├── generation/
│       │   ├── zone.prompt.j2         # Jinja2 template for zone generation
│       │   ├── puzzle.prompt.j2       # Jinja2 template for puzzle generation
│       │   ├── npc.prompt.j2          # Jinja2 template for NPC generation
│       │   └── item.prompt.j2         # Jinja2 template for item generation
│       ├── starter/
│       │   └── crossroads/
│       │       ├── zone.yaml
│       ���       ├── narrative.md
│       │       ├���─ old_merchant/
│       ��       │   └── npc.yaml
│       │       └── broken_signpost/
│       │           ├── puzzle.yaml
│       │           ├── validate.py
│       │           └── solution_stub.py
│       └── companions/
│           ├── scout.yaml
│           ├─�� scholar.yaml
│           ├── tinker.yaml
│           └── cartographer.yaml
├── templates/
│   └── CLAUDE.md.j2                   # Jinja2 template for generated CLAUDE.md
├── tests/
│   ├── conftest.py                    # shared fixtures: tmp game dirs, mock API
│   ├���─ test_state.py
│   ├���─ test_validator.py
│   ├─�� test_profile.py
│   ├── test_generator.py
│   ├── test_init.py
│   ├── test_cli.py
│   └── test_e2e.py                    # end-to-end: init → move → solve flow
└── README.md
```

---

### Task 1: Project Scaffolding & Package Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/lifesim/__init__.py`
- Create: `src/lifesim/cli.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /path/to/agentic-quest
git init
echo "__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.superpowers/
" > .gitignore
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "lifesim"
version = "0.1.0"
description = "LLM-powered text RPG engine"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
    "anthropic>=0.40",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]

[project.scripts]
lifesim = "lifesim.cli:main"
engine = "lifesim.cli:engine"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 3: Create minimal CLI entry point**

```python
# src/lifesim/__init__.py
"""LifeSim — LLM-powered text RPG engine."""
```

```python
# src/lifesim/cli.py
"""CLI entry points for lifesim."""
import click


@click.group()
def main():
    """LifeSim — create and manage LLM-powered text RPG adventures."""
    pass


@main.command()
@click.argument("name")
@click.option("--preset", default="fantasy", help="World preset to use.")
@click.option("--mode", type=click.Choice(["story", "technical"]), default="story", help="Player mode.")
def new(name: str, preset: str, mode: str):
    """Create a new adventure."""
    click.echo(f"Creating adventure '{name}' with preset '{preset}' in {mode} mode...")


@click.group()
def engine():
    """In-game engine commands (called by Claude)."""
    pass


@engine.command()
def status():
    """Show current game state."""
    click.echo("No active game.")
```

- [ ] **Step 4: Create test conftest with shared fixtures**

```python
# tests/conftest.py
"""Shared test fixtures."""
import os
import shutil
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_game_dir(tmp_path: Path) -> Path:
    """Create a temporary game directory with minimal structure."""
    game_dir = tmp_path / "test-adventure"
    game_dir.mkdir()
    (game_dir / "world").mkdir()
    (game_dir / "player").mkdir()

    # Minimal world meta
    meta = {
        "seed": 42,
        "preset": "fantasy",
        "mode": "story",
    }
    (game_dir / "world" / "_meta.yaml").write_text(yaml.dump(meta))

    # Minimal player state
    player_state = {
        "name": "Testplayer",
        "location": "crossroads",
        "inventory": [],
        "companions": ["scout"],
    }
    (game_dir / "player" / "state.yaml").write_text(yaml.dump(player_state))

    return game_dir


@pytest.fixture
def presets_dir() -> Path:
    """Return the path to the presets directory."""
    return Path(__file__).parent.parent / "presets"


@pytest.fixture
def sample_zone_dir(tmp_game_dir: Path) -> Path:
    """Create a sample zone with a puzzle inside the game dir."""
    zone_dir = tmp_game_dir / "world" / "crossroads"
    zone_dir.mkdir(parents=True)

    zone_yaml = {
        "name": "The Crossroads",
        "description": "A weathered signpost marks the meeting of three paths.",
        "connections": {
            "dark_forest": {"name": "Dark Forest", "teaser": "Twisted trees loom ahead.", "status": "stub"},
            "river_valley": {"name": "River Valley", "teaser": "The sound of rushing water.", "status": "stub"},
        },
        "npcs": ["old_merchant"],
        "puzzles": ["broken_signpost"],
    }
    (zone_dir / "zone.yaml").write_text(yaml.dump(zone_yaml))
    (zone_dir / "narrative.md").write_text(
        "You stand at a crossroads. A weathered signpost leans to one side, "
        "its arms pointing in three directions. An old merchant sits nearby, "
        "arranging strange wares on a threadbare blanket.\n"
    )

    # NPC
    npc_dir = zone_dir / "old_merchant"
    npc_dir.mkdir()
    npc_yaml = {
        "name": "Old Merchant",
        "description": "A wizened figure with knowing eyes.",
        "dialogue": {
            "greeting": "Ah, a traveler! The roads are strange these days...",
            "hint": "The stars follow the sun, they say. Always have.",
        },
    }
    (npc_dir / "npc.yaml").write_text(yaml.dump(npc_yaml))

    # Puzzle
    puzzle_dir = zone_dir / "broken_signpost"
    puzzle_dir.mkdir()
    puzzle_yaml = {
        "name": "The Broken Signpost",
        "narrative": "The signpost's arms have fallen. Three carved symbols — a sun, moon, and star — lie in the dirt. Perhaps if arranged correctly, the signpost would point the way.",
        "hints": [
            "The merchant mentioned the stars follow the sun...",
            "Moon reflects the sun's light — it comes second.",
        ],
        "difficulty": 1,
        "type": "function_completion",
        "requires_tools": [],
    }
    (puzzle_dir / "puzzle.yaml").write_text(yaml.dump(puzzle_yaml))

    validate_py = '''"""Validator for the Broken Signpost puzzle."""


def validate(solution_fn):
    """The solution function should sort celestial symbols in the correct order.

    The correct order is: sun first (source of light), moon second (reflects sun),
    star last (most distant).
    """
    assert solution_fn(["moon", "star", "sun"]) == ["sun", "moon", "star"]
    assert solution_fn(["star", "sun", "moon"]) == ["sun", "moon", "star"]
    assert solution_fn(["sun", "moon", "star"]) == ["sun", "moon", "star"]
    return True
'''
    (puzzle_dir / "validate.py").write_text(validate_py)

    stub_py = '''"""Arrange the celestial symbols in the correct order to fix the signpost."""


def solve(symbols: list[str]) -> list[str]:
    """Given a list of celestial symbols ('sun', 'moon', 'star'),
    return them in the correct order to repair the signpost."""
    pass
'''
    (puzzle_dir / "solution_stub.py").write_text(stub_py)

    return zone_dir


@pytest.fixture(autouse=True)
def no_anthropic_calls(monkeypatch):
    """Prevent accidental real API calls in tests."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
```

- [ ] **Step 5: Install in dev mode and verify**

```bash
cd /path/to/agentic-quest
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
lifesim --help
engine --help
pytest tests/ -v --tb=short
```

Expected: Both CLI commands show help text. Pytest discovers conftest but no tests yet (0 collected).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/conftest.py .gitignore
git commit -m "feat: project scaffolding with CLI entry points and test fixtures"
```

---

### Task 2: GameState — Read/Write Game State Files

**Files:**
- Create: `src/lifesim/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests for GameState**

```python
# tests/test_state.py
"""Tests for GameState."""
from pathlib import Path

import yaml

from lifesim.state import GameState


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

        # Verify persisted to disk
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/agentic-quest
source .venv/bin/activate
pytest tests/test_state.py -v --tb=short
```

Expected: All tests FAIL with `ModuleNotFoundError: No module named 'lifesim.state'`

- [ ] **Step 3: Implement GameState**

```python
# src/lifesim/state.py
"""Game state management — reads/writes player and world YAML files."""
from pathlib import Path

import yaml


class GameState:
    """Manages the game directory's file-based state."""

    def __init__(self, game_dir: Path):
        self.game_dir = Path(game_dir)
        if not self.game_dir.exists():
            raise FileNotFoundError(f"Game directory not found: {self.game_dir}")

        self._player_path = self.game_dir / "player" / "state.yaml"
        self._meta_path = self.game_dir / "world" / "_meta.yaml"

        self.player = self._load_yaml(self._player_path)
        self.meta = self._load_yaml(self._meta_path)

    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text()) or {}

    def _save_player(self):
        self._player_path.write_text(yaml.dump(self.player, default_flow_style=False))

    # --- Zones ---

    def get_zone(self, zone_id: str) -> dict | None:
        zone_path = self.game_dir / "world" / zone_id / "zone.yaml"
        if not zone_path.exists():
            return None
        return yaml.safe_load(zone_path.read_text())

    def get_zone_narrative(self, zone_id: str) -> str:
        narrative_path = self.game_dir / "world" / zone_id / "narrative.md"
        if not narrative_path.exists():
            return ""
        return narrative_path.read_text()

    def get_paths(self, zone_id: str) -> list[dict]:
        zone = self.get_zone(zone_id)
        if not zone or "connections" not in zone:
            return []
        return [
            {"id": conn_id, **conn_data}
            for conn_id, conn_data in zone["connections"].items()
        ]

    # --- Player mutation ---

    def move_player(self, zone_id: str):
        self.player["location"] = zone_id
        self._save_player()

    def add_to_inventory(self, item: str):
        if item not in self.player["inventory"]:
            self.player["inventory"].append(item)
            self._save_player()

    def add_companion(self, companion: str):
        if companion not in self.player["companions"]:
            self.player["companions"].append(companion)
            self._save_player()

    # --- Puzzles ---

    def get_puzzle(self, zone_id: str, puzzle_id: str) -> dict | None:
        puzzle_path = self.game_dir / "world" / zone_id / puzzle_id / "puzzle.yaml"
        if not puzzle_path.exists():
            return None
        return yaml.safe_load(puzzle_path.read_text())

    def get_puzzle_hint(self, zone_id: str, puzzle_id: str, hint_index: int = 0) -> str:
        puzzle = self.get_puzzle(zone_id, puzzle_id)
        if not puzzle or "hints" not in puzzle:
            return ""
        hints = puzzle["hints"]
        if hint_index >= len(hints):
            return hints[-1] if hints else ""
        return hints[hint_index]

    def mark_puzzle_solved(self, zone_id: str, puzzle_id: str):
        puzzle_path = self.game_dir / "world" / zone_id / puzzle_id / "puzzle.yaml"
        puzzle = yaml.safe_load(puzzle_path.read_text())
        puzzle["solved"] = True
        puzzle_path.write_text(yaml.dump(puzzle, default_flow_style=False))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/state.py tests/test_state.py
git commit -m "feat: GameState class for reading/writing game state files"
```

---

### Task 3: PuzzleValidator — Run Validator Functions in Subprocess

**Files:**
- Create: `src/lifesim/validator.py`
- Create: `tests/test_validator.py`

- [ ] **Step 1: Write failing tests for PuzzleValidator**

```python
# tests/test_validator.py
"""Tests for PuzzleValidator."""
from pathlib import Path
from textwrap import dedent

from lifesim.validator import PuzzleValidator, ValidationResult


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_validator.py -v --tb=short
```

Expected: FAIL with `ModuleNotFoundError: No module named 'lifesim.validator'`

- [ ] **Step 3: Implement PuzzleValidator**

```python
# src/lifesim/validator.py
"""Puzzle validator — runs validate.py against a solution in a subprocess."""
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


_RUNNER_TEMPLATE = """
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
    print(f"FAIL: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_validator.py -v --tb=short
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/validator.py tests/test_validator.py
git commit -m "feat: PuzzleValidator runs validate.py against solutions in subprocess"
```

---

### Task 4: PlayerProfile — Track Player Behavior

**Files:**
- Create: `src/lifesim/profile.py`
- Create: `tests/test_profile.py`

- [ ] **Step 1: Write failing tests for PlayerProfile**

```python
# tests/test_profile.py
"""Tests for PlayerProfile."""
from pathlib import Path

import yaml

from lifesim.profile import PlayerProfile


class TestPlayerProfileInit:
    def test_creates_default_profile(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        assert profile.data["skill_signals"]["avg_attempts_per_puzzle"] == 0
        assert profile.data["skill_signals"]["technical_comfort"] == 0.0
        assert profile.data["generation_hints"]["difficulty_target"] == 1.0

    def test_loads_existing_profile(self, tmp_game_dir: Path):
        profile_path = tmp_game_dir / "player" / "profile.yaml"
        profile_path.write_text(yaml.dump({
            "skill_signals": {
                "puzzle_types_enjoyed": ["function_completion"],
                "avg_attempts_per_puzzle": 2.3,
                "technical_comfort": 0.5,
            },
            "generation_hints": {
                "difficulty_target": 3.0,
            },
        }))
        profile = PlayerProfile(tmp_game_dir / "player")
        assert profile.data["skill_signals"]["avg_attempts_per_puzzle"] == 2.3
        assert profile.data["generation_hints"]["difficulty_target"] == 3.0


class TestPlayerProfileTracking:
    def test_record_puzzle_attempt(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        profile.record_puzzle_attempt("broken_signpost", solved=False)
        profile.record_puzzle_attempt("broken_signpost", solved=True)
        assert profile.data["skill_signals"]["avg_attempts_per_puzzle"] == 2.0

    def test_record_puzzle_updates_enjoyed_types(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        profile.record_puzzle_attempt("p1", solved=True, puzzle_type="function_completion")
        assert "function_completion" in profile.data["skill_signals"]["puzzle_types_enjoyed"]

    def test_difficulty_adjusts_on_easy_solves(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        # Solve 3 puzzles on first attempt → difficulty should increase
        for i in range(3):
            profile.record_puzzle_attempt(f"p{i}", solved=True)
        assert profile.data["generation_hints"]["difficulty_target"] > 1.0

    def test_difficulty_adjusts_on_struggles(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        profile.data["generation_hints"]["difficulty_target"] = 3.0
        # Fail 5 times on a single puzzle
        for _ in range(5):
            profile.record_puzzle_attempt("hard_one", solved=False)
        assert profile.data["generation_hints"]["difficulty_target"] < 3.0

    def test_persists_to_disk(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        profile.record_puzzle_attempt("p1", solved=True)
        profile.save()

        reloaded = yaml.safe_load(
            (tmp_game_dir / "player" / "profile.yaml").read_text()
        )
        assert reloaded["skill_signals"]["avg_attempts_per_puzzle"] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_profile.py -v --tb=short
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement PlayerProfile**

```python
# src/lifesim/profile.py
"""Player profile — tracks behavior signals and adapts generation hints."""
from pathlib import Path

import yaml

_DEFAULT_PROFILE = {
    "skill_signals": {
        "puzzle_types_enjoyed": [],
        "avg_attempts_per_puzzle": 0,
        "preferred_interaction": "balanced",
        "technical_comfort": 0.0,
        "language_patterns": [],
        "interests_detected": [],
    },
    "generation_hints": {
        "more_of": [],
        "less_of": [],
        "difficulty_target": 1.0,
    },
}


class PlayerProfile:
    """Tracks player behavior and maintains adaptive generation hints."""

    def __init__(self, player_dir: Path):
        self.player_dir = Path(player_dir)
        self._path = self.player_dir / "profile.yaml"
        self._puzzle_attempts: dict[str, int] = {}
        self._total_puzzles_solved = 0
        self._total_attempts = 0

        if self._path.exists():
            self.data = yaml.safe_load(self._path.read_text()) or {}
        else:
            self.data = _deep_copy_default()

    def record_puzzle_attempt(
        self, puzzle_id: str, solved: bool, puzzle_type: str | None = None
    ):
        self._puzzle_attempts.setdefault(puzzle_id, 0)
        self._puzzle_attempts[puzzle_id] += 1
        self._total_attempts += 1

        if solved:
            self._total_puzzles_solved += 1
            attempts_this_puzzle = self._puzzle_attempts[puzzle_id]

            # Update avg attempts
            if self._total_puzzles_solved > 0:
                self.data["skill_signals"]["avg_attempts_per_puzzle"] = (
                    self._total_attempts / self._total_puzzles_solved
                )

            # Track enjoyed puzzle types
            if puzzle_type:
                enjoyed = self.data["skill_signals"]["puzzle_types_enjoyed"]
                if puzzle_type not in enjoyed:
                    enjoyed.append(puzzle_type)

            # Adjust difficulty: easy solves (1 attempt) push up, struggles push down
            if attempts_this_puzzle == 1:
                self.data["generation_hints"]["difficulty_target"] = min(
                    10.0,
                    self.data["generation_hints"]["difficulty_target"] + 0.3,
                )
        else:
            # Update avg even on failure for tracking
            if self._total_puzzles_solved > 0:
                self.data["skill_signals"]["avg_attempts_per_puzzle"] = (
                    self._total_attempts / self._total_puzzles_solved
                )

            # Many failures on same puzzle → ease off
            if self._puzzle_attempts[puzzle_id] >= 4:
                self.data["generation_hints"]["difficulty_target"] = max(
                    0.5,
                    self.data["generation_hints"]["difficulty_target"] - 0.2,
                )

    def save(self):
        self._path.write_text(yaml.dump(self.data, default_flow_style=False))


def _deep_copy_default() -> dict:
    """Return a fresh copy of the default profile."""
    return {
        "skill_signals": {
            "puzzle_types_enjoyed": [],
            "avg_attempts_per_puzzle": 0,
            "preferred_interaction": "balanced",
            "technical_comfort": 0.0,
            "language_patterns": [],
            "interests_detected": [],
        },
        "generation_hints": {
            "more_of": [],
            "less_of": [],
            "difficulty_target": 1.0,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_profile.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/profile.py tests/test_profile.py
git commit -m "feat: PlayerProfile tracks puzzle attempts and adjusts difficulty"
```

---

### Task 5: ZoneGenerator — Create Zones via Anthropic API

**Files:**
- Create: `src/lifesim/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests for ZoneGenerator (mocked API)**

```python
# tests/test_generator.py
"""Tests for ZoneGenerator."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from lifesim.generator import ZoneGenerator


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


class TestZoneGeneratorStub:
    def test_generates_zone_stub(self, tmp_game_dir: Path, presets_dir: Path):
        gen = ZoneGenerator(
            game_dir=tmp_game_dir,
            preset_dir=presets_dir / "fantasy",
            api_key="test-key",
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(json.dumps({
            "name": "Dark Forest",
            "teaser": "Twisted trees loom in perpetual twilight.",
            "connections": {},
        }))
        gen._client = mock_client

        stub = gen.generate_zone_stub("dark_forest", context={
            "adjacent_zones": ["crossroads"],
            "player_profile": {},
            "difficulty": 1.0,
        })
        assert stub["name"] == "Dark Forest"
        assert "teaser" in stub


class TestZoneGeneratorFull:
    def test_generates_full_zone_files(self, tmp_game_dir: Path, presets_dir: Path):
        zone_yaml = {
            "name": "Dark Forest",
            "description": "A forest where the canopy blocks all sunlight.",
            "connections": {
                "crossroads": {"name": "The Crossroads", "teaser": "Back to safety.", "status": "explored"},
                "hidden_grove": {"name": "Hidden Grove", "teaser": "A glimmer through the trees.", "status": "stub"},
            },
            "npcs": [],
            "puzzles": ["tangled_roots"],
        }
        narrative = "The trees close in around you. Gnarled roots criss-cross the path.\n"
        puzzle_yaml = {
            "name": "The Tangled Roots",
            "narrative": "Massive roots block the path. They seem to form a pattern.",
            "hints": ["Look for the thinnest root — it's the key."],
            "difficulty": 2,
            "type": "function_completion",
            "requires_tools": [],
        }
        validate_py = 'def validate(solution_fn):\n    assert solution_fn([5,2,8,1]) == [1,2,5,8]\n    return True\n'
        stub_py = 'def solve(roots: list[int]) -> list[int]:\n    """Untangle the roots by arranging them smallest to largest."""\n    pass\n'

        # Mock returns a structured response with all file contents
        gen_response = json.dumps({
            "zone": zone_yaml,
            "narrative": narrative,
            "puzzles": [
                {
                    "id": "tangled_roots",
                    "puzzle": puzzle_yaml,
                    "validate_py": validate_py,
                    "solution_stub_py": stub_py,
                }
            ],
        })

        gen = ZoneGenerator(
            game_dir=tmp_game_dir,
            preset_dir=presets_dir / "fantasy",
            api_key="test-key",
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(gen_response)
        gen._client = mock_client

        gen.generate_full_zone("dark_forest", context={
            "adjacent_zones": ["crossroads"],
            "player_profile": {},
            "difficulty": 2.0,
            "pacing": "puzzle",
        })

        # Verify files were created
        zone_dir = tmp_game_dir / "world" / "dark_forest"
        assert zone_dir.exists()
        assert (zone_dir / "zone.yaml").exists()
        assert (zone_dir / "narrative.md").exists()

        loaded_zone = yaml.safe_load((zone_dir / "zone.yaml").read_text())
        assert loaded_zone["name"] == "Dark Forest"

        puzzle_dir = zone_dir / "tangled_roots"
        assert (puzzle_dir / "puzzle.yaml").exists()
        assert (puzzle_dir / "validate.py").exists()
        assert (puzzle_dir / "solution_stub.py").exists()


class TestZoneGeneratorPromptRendering:
    def test_renders_zone_prompt_template(self, presets_dir: Path, tmp_game_dir: Path):
        gen = ZoneGenerator(
            game_dir=tmp_game_dir,
            preset_dir=presets_dir / "fantasy",
            api_key="test-key",
        )
        context = {
            "adjacent_zones": ["crossroads"],
            "player_profile": {"difficulty_target": 2.0},
            "difficulty": 2.0,
            "pacing": "exploration",
            "world_seed": 42,
            "inventory": [],
            "open_puzzles": [],
        }
        rendered = gen._render_prompt("zone.prompt.j2", context)
        assert "crossroads" in rendered
        assert len(rendered) > 50  # sanity check — not empty
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v --tb=short
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the fantasy preset prompt templates**

```yaml
# presets/fantasy/preset.yaml
name: "Fantasy"
description: "A classic fantasy world of forests, dungeons, and magic."
default_seed: 42
starter_zone: "crossroads"
```

```markdown
<!-- presets/fantasy/voice.md -->
# Fantasy Voice Guide

You are a narrator in a classic fantasy world. Your tone is:
- **Evocative but not purple** — vivid descriptions without overwrought prose
- **Warm and inviting** — the world is dangerous but wondrous
- **Hints of mystery** — every location suggests deeper secrets
- **Grounded** — fantasy elements feel natural, not forced

Use second person: "You step into the clearing..." not "The player steps..."

Avoid: modern slang, meta-references, breaking the fourth wall.
Prefer: sensory details (sounds, smells, textures), NPC personality in dialogue.
```

```jinja2
{# presets/fantasy/generation/zone.prompt.j2 #}
Generate a zone for a fantasy world. Return a JSON object with these keys:
- "zone": a zone.yaml object with name, description, connections (dict of zone_id → {name, teaser, status: "stub"}), npcs (list of ids), puzzles (list of ids)
- "narrative": a 2-3 paragraph narrative.md description in second person
- "puzzles": list of puzzle objects (if pacing calls for one), each with: id, puzzle (puzzle.yaml object), validate_py (Python source), solution_stub_py (Python source)

Context:
- Adjacent zones: {{ adjacent_zones | tojson }}
- Player profile: {{ player_profile | tojson }}
- Difficulty target: {{ difficulty }}
- Pacing hint: {{ pacing }}
- World seed: {{ world_seed | default(42) }}
- Player inventory: {{ inventory | default([]) | tojson }}
- Unsolved puzzles: {{ open_puzzles | default([]) | tojson }}

Rules:
- Zone connections should include a path back to the zone the player came from (status: "explored") and 1-3 new connections (status: "stub")
- If pacing is "puzzle", include exactly one puzzle of type "function_completion" at the target difficulty
- If pacing is "exploration", no puzzle — focus on rich narrative, NPCs, or discoverable items
- Validators must be self-contained Python with a validate(solution_fn) signature
- Solution stubs must have a solve() function with a descriptive docstring
- Puzzle difficulty {{ difficulty }}: 1=trivial (sort a list), 2=easy (simple logic), 3=medium (algorithm), 4=hard (multi-step), 5=very hard

Return ONLY valid JSON, no markdown fencing.
```

```jinja2
{# presets/fantasy/generation/puzzle.prompt.j2 #}
Generate a puzzle for a fantasy world zone. Return a JSON object with:
- "id": snake_case puzzle id
- "puzzle": puzzle.yaml object with name, narrative, hints (list of 2-3), difficulty, type ("function_completion"), requires_tools (list)
- "validate_py": Python source for validate.py — must define validate(solution_fn) that asserts expected behavior
- "solution_stub_py": Python source for solution_stub.py — must define solve() with a descriptive docstring

Context:
- Zone: {{ zone_name }}
- Zone description: {{ zone_description }}
- Difficulty target: {{ difficulty }}
- Player interests: {{ interests | default([]) | tojson }}

The puzzle should feel like a natural part of the zone. The narrative should describe a physical/magical obstacle.
The validator should test 2-4 cases. Keep the solve() function signature simple.

Return ONLY valid JSON, no markdown fencing.
```

```jinja2
{# presets/fantasy/generation/npc.prompt.j2 #}
Generate an NPC for a fantasy world. Return a JSON object (npc.yaml format):
- name: display name
- description: 1-2 sentence physical description
- dialogue: dict with "greeting" and "hint" keys (short dialogue lines)

Context:
- Zone: {{ zone_name }}
- Zone description: {{ zone_description }}
- Player interests: {{ interests | default([]) | tojson }}

Return ONLY valid JSON, no markdown fencing.
```

```jinja2
{# presets/fantasy/generation/item.prompt.j2 #}
Generate a discoverable item/tool for a fantasy world. Return a JSON object (item.yaml format):
- name: display name
- description: 1-2 sentence description
- ability: what it enables (narrative description)
- engine_capability: what engine feature it maps to (e.g., "farsight", "fast_travel", "hint_reveal")

Context:
- Zone: {{ zone_name }}
- Player profile: {{ player_profile | tojson }}
- Player inventory: {{ inventory | default([]) | tojson }}

Return ONLY valid JSON, no markdown fencing.
```

- [ ] **Step 4: Create starter zone and companion files for fantasy preset**

The starter crossroads zone files match what we defined in `conftest.py`. Create them as actual preset files:

```yaml
# presets/fantasy/starter/crossroads/zone.yaml
name: "The Crossroads"
description: "A weathered signpost marks the meeting of three paths."
connections:
  dark_forest:
    name: "Dark Forest"
    teaser: "Twisted trees loom ahead."
    status: "stub"
  river_valley:
    name: "River Valley"
    teaser: "The sound of rushing water."
    status: "stub"
npcs:
  - old_merchant
puzzles:
  - broken_signpost
```

```markdown
<!-- presets/fantasy/starter/crossroads/narrative.md -->
You stand at a crossroads beneath an open sky. A weathered signpost leans to one side, its three arms pointing in different directions — though the carved symbols on each arm have faded beyond reading.

An old merchant sits cross-legged nearby, arranging curious wares on a threadbare blanket. Strange trinkets glint in the sunlight: a compass that seems to spin of its own accord, a glass vial filled with what looks like captured starlight, and a small leather-bound book with no title.

The air carries the scent of pine from the north and damp earth from the east. A well-worn path leads south, disappearing into rolling green hills.
```

```yaml
# presets/fantasy/starter/crossroads/old_merchant/npc.yaml
name: "Old Merchant"
description: "A wizened figure with knowing eyes and a sly smile."
dialogue:
  greeting: "Ah, a traveler! The roads are strange these days. Not many folk pass through the crossroads anymore."
  hint: "The stars follow the sun, they say. Always have. The moon? Well, she's always in between, isn't she? Reflecting what she borrows."
  farewell: "Safe travels, friend. And remember — the signpost remembers the way, even if we forget."
```

```yaml
# presets/fantasy/starter/crossroads/broken_signpost/puzzle.yaml
name: "The Broken Signpost"
narrative: "The signpost's arms have fallen and lie in the dirt. Three carved symbols — a sun, a moon, and a star — are etched into the wooden planks. If you could arrange them in the correct order from top to bottom, the signpost might point the way again."
hints:
  - "The merchant mentioned the stars follow the sun..."
  - "Moon reflects the sun's light — it must come between them."
  - "Source of light first, reflection second, most distant last."
difficulty: 1
type: "function_completion"
requires_tools: []
```

```python
# presets/fantasy/starter/crossroads/broken_signpost/validate.py
"""Validator for the Broken Signpost puzzle."""


def validate(solution_fn):
    """The solution function should sort celestial symbols in the correct order.

    The correct order is: sun first (source of light), moon second (reflects sun),
    star last (most distant).
    """
    assert solution_fn(["moon", "star", "sun"]) == ["sun", "moon", "star"]
    assert solution_fn(["star", "sun", "moon"]) == ["sun", "moon", "star"]
    assert solution_fn(["sun", "moon", "star"]) == ["sun", "moon", "star"]
    return True
```

```python
# presets/fantasy/starter/crossroads/broken_signpost/solution_stub.py
"""Arrange the celestial symbols in the correct order to fix the signpost."""


def solve(symbols: list[str]) -> list[str]:
    """Given a list of celestial symbols ('sun', 'moon', 'star'),
    return them in the correct order to repair the signpost.

    Think about the relationship between these celestial bodies.
    Which one is the source? Which one reflects? Which is farthest away?
    """
    pass
```

```yaml
# presets/fantasy/companions/scout.yaml
archetype: "scout"
name: "Lyra"
title: "Wayfinder"
description: "A keen-eyed ranger with a tattered map always in hand."
personality: "Cautious but curious. Speaks in short, observational sentences. Trusts her instincts."
greeting: "I've been watching the roads. Something's shifted — the paths don't lead where they used to. Stay close, and I'll keep us on track."
abilities:
  - name: "Farsight"
    description: "Scan an adjacent zone before entering"
    engine_command: "scout"
  - name: "Track"
    description: "Find hidden paths in the current zone"
    engine_command: "scout --hidden"
```

```yaml
# presets/fantasy/companions/scholar.yaml
archetype: "scholar"
name: "Eamon"
title: "Lorekeeper"
description: "An elderly scholar carrying a staff hung with tiny glass lanterns."
personality: "Thoughtful and verbose. Loves to explain things. Occasionally distracted by his own tangents."
greeting: "Fascinating! A fellow seeker of knowledge? Or perhaps just a seeker of answers — there is a difference, you know."
abilities:
  - name: "Lore"
    description: "Research deep context about the current zone or puzzle"
    engine_command: "research"
  - name: "Analyze"
    description: "Study a puzzle's mechanics for additional hints"
    engine_command: "research --puzzle"
```

```yaml
# presets/fantasy/companions/tinker.yaml
archetype: "tinker"
name: "Wrench"
title: "Artificer"
description: "A stout, soot-smudged inventor with goggles perched on their forehead."
personality: "Enthusiastic and hands-on. Talks while working. Sees everything as a mechanism to be understood."
greeting: "Oh! Another pair of hands! Brilliant. I've got about twelve things half-built — pick one and let's finish it together."
abilities:
  - name: "Craft"
    description: "Build a solution to a puzzle or obstacle"
    engine_command: "craft"
  - name: "Repair"
    description: "Fix a broken mechanism"
    engine_command: "craft --repair"
```

```yaml
# presets/fantasy/companions/cartographer.yaml
archetype: "cartographer"
name: "Sable"
title: "Mapmaker"
description: "A quiet figure in dark robes, fingers perpetually stained with ink."
personality: "Speaks rarely but precisely. Has an uncanny memory for places. Draws constantly."
greeting: "*looks up from a half-finished map* You've been to places I haven't charted yet. That makes you interesting."
abilities:
  - name: "Chart"
    description: "Render a map of explored areas"
    engine_command: "map"
  - name: "Remember"
    description: "Recall details from previously visited zones"
    engine_command: "map --recall"
```

- [ ] **Step 5: Implement ZoneGenerator**

```python
# src/lifesim/generator.py
"""Zone generator — creates world content via Anthropic API."""
import json
from pathlib import Path

import yaml
from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader


class ZoneGenerator:
    """Generates zones, puzzles, and NPCs using LLM + preset prompt templates."""

    def __init__(self, game_dir: Path, preset_dir: Path, api_key: str):
        self.game_dir = Path(game_dir)
        self.preset_dir = Path(preset_dir)
        self._client = Anthropic(api_key=api_key)
        self._jinja = Environment(
            loader=FileSystemLoader(str(self.preset_dir / "generation")),
            keep_trailing_newline=True,
        )

    def _render_prompt(self, template_name: str, context: dict) -> str:
        template = self._jinja.get_template(template_name)
        return template.render(**context)

    def _call_llm(self, prompt: str) -> str:
        response = self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def generate_zone_stub(self, zone_id: str, context: dict) -> dict:
        prompt = self._render_prompt("zone.prompt.j2", context)
        prompt += "\n\nGenerate ONLY a stub with: name, teaser, connections. Keep it brief."
        raw = self._call_llm(prompt)
        return json.loads(raw)

    def generate_full_zone(self, zone_id: str, context: dict):
        prompt = self._render_prompt("zone.prompt.j2", context)
        raw = self._call_llm(prompt)
        data = json.loads(raw)

        zone_dir = self.game_dir / "world" / zone_id
        zone_dir.mkdir(parents=True, exist_ok=True)

        # Write zone.yaml
        (zone_dir / "zone.yaml").write_text(
            yaml.dump(data["zone"], default_flow_style=False)
        )

        # Write narrative.md
        (zone_dir / "narrative.md").write_text(data["narrative"])

        # Write puzzles
        for puzzle_data in data.get("puzzles", []):
            puzzle_id = puzzle_data["id"]
            puzzle_dir = zone_dir / puzzle_id
            puzzle_dir.mkdir(exist_ok=True)

            (puzzle_dir / "puzzle.yaml").write_text(
                yaml.dump(puzzle_data["puzzle"], default_flow_style=False)
            )
            (puzzle_dir / "validate.py").write_text(puzzle_data["validate_py"])
            (puzzle_dir / "solution_stub.py").write_text(puzzle_data["solution_stub_py"])
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v --tb=short
```

Expected: All tests PASS (API calls are mocked).

- [ ] **Step 7: Commit**

```bash
git add src/lifesim/generator.py tests/test_generator.py presets/
git commit -m "feat: ZoneGenerator creates zones via Anthropic API with fantasy preset"
```

---

### Task 6: GameInitializer — Scaffold New Adventures

**Files:**
- Create: `src/lifesim/init.py`
- Create: `templates/CLAUDE.md.j2`
- Create: `tests/test_init.py`

- [ ] **Step 1: Write failing tests for GameInitializer**

```python
# tests/test_init.py
"""Tests for GameInitializer."""
from pathlib import Path

import yaml

from lifesim.init import GameInitializer


class TestGameInitializer:
    def test_creates_game_directory(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        assert game_dir.exists()
        assert (game_dir / "world").exists()
        assert (game_dir / "player").exists()

    def test_copies_starter_zone(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        crossroads = game_dir / "world" / "crossroads"
        assert crossroads.exists()
        assert (crossroads / "zone.yaml").exists()
        assert (crossroads / "narrative.md").exists()
        assert (crossroads / "broken_signpost" / "validate.py").exists()

    def test_creates_world_meta(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        meta = yaml.safe_load((game_dir / "world" / "_meta.yaml").read_text())
        assert meta["preset"] == "fantasy"
        assert meta["mode"] == "story"
        assert "seed" in meta

    def test_creates_player_state(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        player = yaml.safe_load((game_dir / "player" / "state.yaml").read_text())
        assert player["location"] == "crossroads"
        assert "scout" in player["companions"]

    def test_generates_claude_md(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        claude_md = (game_dir / "CLAUDE.md").read_text()
        assert "engine" in claude_md.lower()
        assert "story" in claude_md.lower() or "STORY" in claude_md

    def test_technical_mode_claude_md(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="technical")

        claude_md = (game_dir / "CLAUDE.md").read_text()
        assert "technical" in claude_md.lower() or "TECHNICAL" in claude_md

    def test_copies_companion_files(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")

        companions_dir = game_dir / "player" / "companions"
        assert (companions_dir / "scout.yaml").exists()
        assert (companions_dir / "scholar.yaml").exists()
        assert (companions_dir / "tinker.yaml").exists()
        assert (companions_dir / "cartographer.yaml").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_init.py -v --tb=short
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the CLAUDE.md Jinja2 template**

```jinja2
{# templates/CLAUDE.md.j2 #}
# LifeSim — {{ preset_name }}

You are the narrator of a {{ genre }} world. The player is exploring an infinite, procedurally generated world full of puzzles, NPCs, and discoverable tools.

## Your Role

- Narrate the world vividly using the voice guide below
- Interpret player intent and translate it into engine commands
- **NEVER modify game files directly** — always use `engine` CLI commands via Bash
- Present choices to guide the player, but accept freeform input
- Voice all companions with distinct personalities (see their yaml files in `player/companions/`)

## Voice Guide

{{ voice_guide }}

## Player Mode: {{ mode | upper }}

{% if mode == "story" %}
- Player is in **STORY MODE** — NEVER show code, validators, file paths, or technical output
- Translate their natural language descriptions into solutions behind the scenes
- When running `engine solve`, write the solution file yourself based on the player's description, then submit it
- Narrate success/failure as world events: "The signpost clicks into place!" not "All assertions passed"
- If the validator fails, narrate it as a story event and give a narrative hint, not a technical error
{% elif mode == "technical" %}
- Player is in **TECHNICAL MODE** — show puzzle stubs and validator signatures
- Let them write code directly, or describe logic for you to translate
- Show engine command output alongside narrative
- You can reference file paths and puzzle structure
{% endif %}

## Companions

You voice all companions. Each has a distinct personality defined in `player/companions/*.yaml`.
When the player addresses a companion by name, respond in character AND dispatch the appropriate engine command.

| Companion | Trigger | Engine Command |
|-----------|---------|---------------|
{% for companion in companions %}
| {{ companion.name }} ({{ companion.title }}) | "{{ companion.name }}, ..." | `engine {{ companion.abilities[0].engine_command }}` |
{% endfor %}

## Engine Commands Reference

```bash
# Check current state (run this at session start!)
engine status

# Look around current zone
engine look

# See available paths
engine paths

# Move to a zone
engine move <zone_id>

# Generate a new zone (for unexpected player actions)
engine generate "<description>"

# View current puzzle
engine puzzle

# Submit a puzzle solution (write solution to a temp file first)
engine solve <puzzle_id> --solution <path_to_solution.py>

# Get a hint
engine hint <puzzle_id>

# Companion abilities
engine scout <direction>          # Scout scans ahead
engine research <topic>           # Scholar investigates
engine craft <description>        # Tinker builds
engine map                        # Cartographer shows map

# Player info
engine inventory
engine companions
engine profile
```

## Game Loop

Every time a new session starts or the player returns:

1. Run `engine status` to understand current state
2. Run `engine look` to get the current zone narrative
3. Narrate where the player is and what they see
4. Present 2-3 choices based on available paths and points of interest
5. Respond to player input — move, solve, explore, talk to NPCs, or anything unexpected
6. After significant actions (solving puzzles, finding items), run `engine profile update`

## Important Rules

- You are the narrator. Stay in character.
- The engine is the source of truth for game state. Always check before assuming.
- If the player tries something the world doesn't support yet, use `engine generate` to create it.
- Celebrate puzzle solves! Make the player feel accomplished.
- If the player seems stuck, have an NPC or companion offer a gentle nudge.
```

- [ ] **Step 4: Implement GameInitializer**

```python
# src/lifesim/init.py
"""Game initializer — scaffolds a new adventure from a preset."""
import random
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


class GameInitializer:
    """Creates a new game directory from a preset template."""

    def __init__(self, presets_dir: Path):
        self.presets_dir = Path(presets_dir)
        self._templates_dir = Path(__file__).parent.parent.parent / "templates"

    def create(self, game_dir: Path, preset: str, mode: str):
        game_dir = Path(game_dir)
        preset_dir = self.presets_dir / preset

        if not preset_dir.exists():
            raise FileNotFoundError(f"Preset not found: {preset}")

        # Create directory structure
        game_dir.mkdir(parents=True, exist_ok=True)
        (game_dir / "world").mkdir(exist_ok=True)
        (game_dir / "player").mkdir(exist_ok=True)
        (game_dir / "player" / "companions").mkdir(exist_ok=True)

        # Load preset metadata
        preset_meta = yaml.safe_load(
            (preset_dir / "preset.yaml").read_text()
        )

        # Copy starter zone
        starter_dir = preset_dir / "starter"
        if starter_dir.exists():
            for zone_dir in starter_dir.iterdir():
                if zone_dir.is_dir():
                    shutil.copytree(zone_dir, game_dir / "world" / zone_dir.name)

        # Copy companion files
        companions_src = preset_dir / "companions"
        if companions_src.exists():
            for comp_file in companions_src.glob("*.yaml"):
                shutil.copy2(comp_file, game_dir / "player" / "companions" / comp_file.name)

        # Create world meta
        meta = {
            "seed": random.randint(1, 999999),
            "preset": preset,
            "mode": mode,
            "preset_name": preset_meta.get("name", preset),
        }
        (game_dir / "world" / "_meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False)
        )

        # Create player state
        starter_zone = preset_meta.get("starter_zone", "crossroads")
        player_state = {
            "name": "Adventurer",
            "location": starter_zone,
            "inventory": [],
            "companions": ["scout"],
            "puzzles_solved": [],
            "zones_visited": [starter_zone],
        }
        (game_dir / "player" / "state.yaml").write_text(
            yaml.dump(player_state, default_flow_style=False)
        )

        # Create initial profile
        from lifesim.profile import PlayerProfile
        profile = PlayerProfile(game_dir / "player")
        profile.save()

        # Generate CLAUDE.md
        self._generate_claude_md(game_dir, preset_dir, preset_meta, mode)

    def _generate_claude_md(
        self, game_dir: Path, preset_dir: Path, preset_meta: dict, mode: str
    ):
        voice_guide = ""
        voice_path = preset_dir / "voice.md"
        if voice_path.exists():
            voice_guide = voice_path.read_text()

        # Load companion data for the template
        companions = []
        companions_dir = preset_dir / "companions"
        if companions_dir.exists():
            for comp_file in sorted(companions_dir.glob("*.yaml")):
                comp = yaml.safe_load(comp_file.read_text())
                companions.append(comp)

        jinja = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            keep_trailing_newline=True,
        )
        template = jinja.get_template("CLAUDE.md.j2")
        claude_md = template.render(
            preset_name=preset_meta.get("name", "Fantasy"),
            genre=preset_meta.get("name", "fantasy").lower(),
            mode=mode,
            voice_guide=voice_guide,
            companions=companions,
        )

        (game_dir / "CLAUDE.md").write_text(claude_md)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_init.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/lifesim/init.py templates/ tests/test_init.py
git commit -m "feat: GameInitializer scaffolds adventures from presets with CLAUDE.md generation"
```

---

### Task 7: Full CLI — Wire Up All Engine Commands

**Files:**
- Modify: `src/lifesim/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI commands**

```python
# tests/test_cli.py
"""Tests for CLI commands."""
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from lifesim.cli import engine, main


class TestLifesimNew:
    def test_creates_adventure_directory(self, tmp_path: Path, presets_dir: Path):
        runner = CliRunner()
        game_dir = tmp_path / "my-adventure"

        with patch("lifesim.cli._find_presets_dir", return_value=presets_dir):
            result = runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "story"])

        assert result.exit_code == 0, result.output
        assert game_dir.exists()
        assert (game_dir / "CLAUDE.md").exists()


class TestEngineStatus:
    def test_shows_player_location(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["status"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower()
        assert "Testplayer" in result.output

    def test_shows_companions(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["status"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert "scout" in result.output.lower()


class TestEngineLook:
    def test_shows_zone_narrative(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["look"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "crossroads" in result.output.lower()


class TestEnginePaths:
    def test_shows_available_paths(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["paths"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "dark_forest" in result.output.lower() or "Dark Forest" in result.output


class TestEngineMove:
    def test_move_to_existing_zone(self, tmp_game_dir: Path, sample_zone_dir: Path):
        # Create a stub dark_forest zone
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
        result = runner.invoke(engine, ["move", "dark_forest"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0

        player = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        assert player["location"] == "dark_forest"


class TestEnginePuzzle:
    def test_shows_puzzle_info(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["puzzle"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "Broken Signpost" in result.output or "broken_signpost" in result.output


class TestEngineSolve:
    def test_correct_solution(self, tmp_game_dir: Path, sample_zone_dir: Path):
        # Write a correct solution file
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
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
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
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
        )
        assert "fail" in result.output.lower() or "error" in result.output.lower()


class TestEngineHint:
    def test_shows_hint(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["hint", "broken_signpost"],
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "merchant" in result.output.lower() or "sun" in result.output.lower()


class TestEngineInventory:
    def test_shows_empty_inventory(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["inventory"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "no items" in result.output.lower()


class TestEngineCompanions:
    def test_lists_companions(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["companions"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "scout" in result.output.lower()


class TestEngineProfile:
    def test_shows_profile(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["profile"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "difficulty" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v --tb=short
```

Expected: Most tests FAIL (commands not implemented yet).

- [ ] **Step 3: Implement full CLI**

```python
# src/lifesim/cli.py
"""CLI entry points for lifesim."""
import json
import os
from pathlib import Path

import click
import yaml

from lifesim.profile import PlayerProfile
from lifesim.state import GameState
from lifesim.validator import PuzzleValidator


def _find_presets_dir() -> Path:
    """Locate the presets directory relative to the package."""
    return Path(__file__).parent.parent.parent / "presets"


def _get_game_dir() -> Path:
    """Get game directory from env var or current directory."""
    env_dir = os.environ.get("LIFESIM_GAME_DIR")
    if env_dir:
        return Path(env_dir)
    cwd = Path.cwd()
    if (cwd / "world" / "_meta.yaml").exists():
        return cwd
    click.echo("Error: not in a game directory. Set LIFESIM_GAME_DIR or cd into a game folder.", err=True)
    raise SystemExit(1)


def _load_state() -> GameState:
    return GameState(_get_game_dir())


# --- lifesim commands (create/manage adventures) ---


@click.group()
def main():
    """LifeSim — create and manage LLM-powered text RPG adventures."""
    pass


@main.command()
@click.argument("path")
@click.option("--preset", default="fantasy", help="World preset to use.")
@click.option("--mode", type=click.Choice(["story", "technical"]), default="story", help="Player mode.")
def new(path: str, preset: str, mode: str):
    """Create a new adventure."""
    from lifesim.init import GameInitializer

    game_dir = Path(path)
    presets_dir = _find_presets_dir()
    init = GameInitializer(presets_dir=presets_dir)
    init.create(game_dir, preset=preset, mode=mode)
    click.echo(f"Adventure created at {game_dir}")
    click.echo(f"Open this folder in Claude Code to start playing!")


# --- engine commands (in-game, called by Claude) ---


@click.group()
def engine():
    """In-game engine commands (called by Claude during gameplay)."""
    pass


@engine.command()
def status():
    """Show current game state summary."""
    gs = _load_state()
    click.echo(f"Player: {gs.player.get('name', 'Unknown')}")
    click.echo(f"Location: {gs.player['location']}")
    click.echo(f"Companions: {', '.join(gs.player.get('companions', []))}")
    click.echo(f"Inventory: {', '.join(gs.player.get('inventory', [])) or 'empty'}")
    click.echo(f"Puzzles solved: {', '.join(gs.player.get('puzzles_solved', [])) or 'none'}")
    click.echo(f"Zones visited: {', '.join(gs.player.get('zones_visited', []))}")


@engine.command()
def look():
    """Describe the current zone."""
    gs = _load_state()
    location = gs.player["location"]
    zone = gs.get_zone(location)
    narrative = gs.get_zone_narrative(location)

    if zone:
        click.echo(f"=== {zone['name']} ===\n")
    if narrative:
        click.echo(narrative)
    else:
        click.echo(f"You are at {location}. (No narrative available.)")

    # Show NPCs
    if zone and zone.get("npcs"):
        click.echo(f"\nNPCs here: {', '.join(zone['npcs'])}")

    # Show puzzles
    if zone and zone.get("puzzles"):
        for puzzle_id in zone["puzzles"]:
            puzzle = gs.get_puzzle(location, puzzle_id)
            if puzzle and not puzzle.get("solved"):
                click.echo(f"\nPuzzle: {puzzle['name']} (unsolved)")
            elif puzzle and puzzle.get("solved"):
                click.echo(f"\nPuzzle: {puzzle['name']} (solved)")


@engine.command()
def paths():
    """Show available paths from current zone."""
    gs = _load_state()
    location = gs.player["location"]
    zone_paths = gs.get_paths(location)

    if not zone_paths:
        click.echo("No paths visible from here.")
        return

    click.echo("Available paths:\n")
    for p in zone_paths:
        status = p.get("status", "unknown")
        teaser = p.get("teaser", "")
        click.echo(f"  {p['id']}: {p['name']} [{status}] — {teaser}")


@engine.command()
@click.argument("zone_id")
def move(zone_id: str):
    """Move to a zone."""
    gs = _load_state()
    zone = gs.get_zone(zone_id)

    if not zone:
        click.echo(f"Zone '{zone_id}' has not been generated yet.")
        click.echo(f"Use 'engine generate \"{zone_id}\"' to create it first.")
        return

    gs.move_player(zone_id)

    # Track visited zones
    visited = gs.player.setdefault("zones_visited", [])
    if zone_id not in visited:
        visited.append(zone_id)
        gs._save_player()

    click.echo(f"Moved to {zone['name']}.")


@engine.command()
@click.argument("description")
def generate(description: str):
    """Generate a new zone (for unexpected player actions)."""
    gs = _load_state()
    meta = gs.meta
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set.", err=True)
        raise SystemExit(1)

    from lifesim.generator import ZoneGenerator

    preset_dir = _find_presets_dir() / meta.get("preset", "fantasy")
    gen = ZoneGenerator(game_dir=gs.game_dir, preset_dir=preset_dir, api_key=api_key)

    # Build context
    location = gs.player["location"]
    profile = PlayerProfile(gs.game_dir / "player")
    context = {
        "adjacent_zones": gs.player.get("zones_visited", []),
        "player_profile": profile.data,
        "difficulty": profile.data["generation_hints"]["difficulty_target"],
        "pacing": "exploration",
        "world_seed": meta.get("seed", 42),
        "inventory": gs.player.get("inventory", []),
        "open_puzzles": [],
    }

    # Generate a zone_id from the description
    zone_id = description.lower().replace(" ", "_")[:30]
    click.echo(f"Generating zone '{zone_id}'...")
    gen.generate_full_zone(zone_id, context)

    # Connect it to current zone
    current_zone = gs.get_zone(location)
    if current_zone:
        connections = current_zone.setdefault("connections", {})
        connections[zone_id] = {
            "name": description,
            "teaser": "A newly discovered area.",
            "status": "explored",
        }
        zone_path = gs.game_dir / "world" / location / "zone.yaml"
        zone_path.write_text(yaml.dump(current_zone, default_flow_style=False))

    click.echo(f"Zone '{zone_id}' generated and connected to {location}.")


@engine.command()
def puzzle():
    """Show current zone's puzzle(s)."""
    gs = _load_state()
    location = gs.player["location"]
    zone = gs.get_zone(location)

    if not zone or not zone.get("puzzles"):
        click.echo("No puzzles in this zone.")
        return

    for puzzle_id in zone["puzzles"]:
        p = gs.get_puzzle(location, puzzle_id)
        if p:
            solved_str = " [SOLVED]" if p.get("solved") else ""
            click.echo(f"=== {p['name']}{solved_str} ===")
            click.echo(f"ID: {puzzle_id}")
            click.echo(f"Difficulty: {p.get('difficulty', '?')}")
            click.echo(f"Type: {p.get('type', 'unknown')}")
            click.echo(f"\n{p.get('narrative', '')}")

            # In technical mode, show stub path
            mode = gs.meta.get("mode", "story")
            if mode == "technical":
                stub_path = gs.game_dir / "world" / location / puzzle_id / "solution_stub.py"
                if stub_path.exists():
                    click.echo(f"\nSolution stub: {stub_path}")
                    click.echo(stub_path.read_text())


@engine.command()
@click.argument("puzzle_id")
@click.option("--solution", required=True, type=click.Path(exists=True), help="Path to solution.py")
def solve(puzzle_id: str, solution: str):
    """Submit a puzzle solution."""
    gs = _load_state()
    location = gs.player["location"]
    puzzle_data = gs.get_puzzle(location, puzzle_id)

    if not puzzle_data:
        click.echo(f"Puzzle '{puzzle_id}' not found in {location}.")
        return

    if puzzle_data.get("solved"):
        click.echo(f"Puzzle '{puzzle_data['name']}' is already solved!")
        return

    validate_path = gs.game_dir / "world" / location / puzzle_id / "validate.py"
    if not validate_path.exists():
        click.echo(f"Error: validator not found at {validate_path}", err=True)
        return

    validator = PuzzleValidator()
    result = validator.run(validate_path, Path(solution))

    if result.passed:
        gs.mark_puzzle_solved(location, puzzle_id)

        # Update profile
        profile = PlayerProfile(gs.game_dir / "player")
        profile.record_puzzle_attempt(
            puzzle_id, solved=True, puzzle_type=puzzle_data.get("type")
        )
        profile.save()

        # Track in player state
        solved_list = gs.player.setdefault("puzzles_solved", [])
        if puzzle_id not in solved_list:
            solved_list.append(puzzle_id)
            gs._save_player()

        click.echo(f"SOLVED: {puzzle_data['name']}")
    else:
        # Update profile for failed attempt
        profile = PlayerProfile(gs.game_dir / "player")
        profile.record_puzzle_attempt(puzzle_id, solved=False)
        profile.save()

        click.echo(f"FAILED: {result.error}")


@engine.command()
@click.argument("puzzle_id")
def hint(puzzle_id: str):
    """Get a hint for a puzzle."""
    gs = _load_state()
    location = gs.player["location"]

    # Track hint index in player state
    hints_used = gs.player.setdefault("hints_used", {})
    hint_index = hints_used.get(puzzle_id, 0)

    hint_text = gs.get_puzzle_hint(location, puzzle_id, hint_index)
    if hint_text:
        click.echo(f"Hint: {hint_text}")
        hints_used[puzzle_id] = hint_index + 1
        gs._save_player()
    else:
        click.echo("No more hints available.")


@engine.command()
def inventory():
    """Show player inventory."""
    gs = _load_state()
    items = gs.player.get("inventory", [])
    if not items:
        click.echo("Inventory is empty. No items yet.")
    else:
        click.echo("Inventory:")
        for item in items:
            click.echo(f"  - {item}")


@engine.command()
def companions():
    """List companions in the party."""
    gs = _load_state()
    comp_list = gs.player.get("companions", [])
    companions_dir = gs.game_dir / "player" / "companions"

    if not comp_list:
        click.echo("You are traveling alone.")
        return

    click.echo("Your companions:\n")
    for comp_id in comp_list:
        comp_file = companions_dir / f"{comp_id}.yaml"
        if comp_file.exists():
            comp = yaml.safe_load(comp_file.read_text())
            click.echo(f"  {comp.get('name', comp_id)} — {comp.get('title', '')}")
            click.echo(f"    {comp.get('description', '')}")
            for ability in comp.get("abilities", []):
                click.echo(f"    • {ability['name']}: {ability['description']}")
            click.echo()
        else:
            click.echo(f"  {comp_id} (no details available)")


@engine.command("map")
def show_map():
    """Show a map of explored zones."""
    gs = _load_state()
    visited = gs.player.get("zones_visited", [])
    location = gs.player["location"]

    click.echo("=== World Map ===\n")
    for zone_id in visited:
        marker = " <-- YOU ARE HERE" if zone_id == location else ""
        zone = gs.get_zone(zone_id)
        name = zone["name"] if zone else zone_id
        click.echo(f"  [{name}]{marker}")
        if zone and zone.get("connections"):
            for conn_id, conn in zone["connections"].items():
                status = conn.get("status", "?")
                if conn_id not in visited:
                    click.echo(f"    → {conn.get('name', conn_id)} [{status}]")


@engine.command()
def profile():
    """Show player profile and adaptation data."""
    gs = _load_state()
    prof = PlayerProfile(gs.game_dir / "player")

    click.echo("=== Player Profile ===\n")
    signals = prof.data.get("skill_signals", {})
    click.echo(f"Avg attempts per puzzle: {signals.get('avg_attempts_per_puzzle', 0):.1f}")
    click.echo(f"Technical comfort: {signals.get('technical_comfort', 0):.1f}")
    click.echo(f"Preferred interaction: {signals.get('preferred_interaction', 'balanced')}")
    click.echo(f"Puzzle types enjoyed: {', '.join(signals.get('puzzle_types_enjoyed', [])) or 'none yet'}")

    hints = prof.data.get("generation_hints", {})
    click.echo(f"\nDifficulty target: {hints.get('difficulty_target', 1.0):.1f}")
    click.echo(f"More of: {', '.join(hints.get('more_of', [])) or 'no preferences yet'}")
    click.echo(f"Less of: {', '.join(hints.get('less_of', [])) or 'no preferences yet'}")


@engine.command()
@click.argument("direction")
def scout(direction: str):
    """Scout an adjacent zone (Scout companion ability)."""
    gs = _load_state()
    if "scout" not in gs.player.get("companions", []):
        click.echo("You don't have a Scout companion yet.")
        return

    location = gs.player["location"]
    zone = gs.get_zone(location)
    if not zone:
        click.echo("Cannot scout from unknown location.")
        return

    connections = zone.get("connections", {})
    if direction in connections:
        conn = connections[direction]
        click.echo(f"Scout report for {conn.get('name', direction)}:")
        click.echo(f"  {conn.get('teaser', 'No details available.')}")

        # Check if full zone exists
        target_zone = gs.get_zone(direction)
        if target_zone:
            click.echo(f"  Status: Explored")
            if target_zone.get("puzzles"):
                click.echo(f"  Contains puzzles: {', '.join(target_zone['puzzles'])}")
        else:
            click.echo(f"  Status: Unexplored — will be generated on entry")
    else:
        click.echo(f"No known path in direction '{direction}'.")


@engine.command()
@click.argument("topic")
def research(topic: str):
    """Scholar researches a topic (Scholar companion ability)."""
    gs = _load_state()
    if "scholar" not in gs.player.get("companions", []):
        click.echo("You don't have a Scholar companion yet.")
        return

    # For MVP, research provides puzzle hints and zone lore
    location = gs.player["location"]
    zone = gs.get_zone(location)

    click.echo(f"Scholar researches '{topic}'...\n")

    # Check if topic matches a puzzle
    if zone and zone.get("puzzles"):
        for puzzle_id in zone["puzzles"]:
            if topic.lower() in puzzle_id.lower() or puzzle_id.lower() in topic.lower():
                puzzle = gs.get_puzzle(location, puzzle_id)
                if puzzle:
                    click.echo(f"Research findings on '{puzzle['name']}':")
                    for h in puzzle.get("hints", []):
                        click.echo(f"  • {h}")
                    return

    click.echo(f"The Scholar ponders '{topic}' but finds no specific information in this zone.")
    click.echo("Try researching a puzzle name for more detailed findings.")


@engine.command()
@click.argument("description")
def craft(description: str):
    """Tinker crafts something (Tinker companion ability)."""
    gs = _load_state()
    if "tinker" not in gs.player.get("companions", []):
        click.echo("You don't have a Tinker companion yet.")
        return

    click.echo(f"The Tinker considers how to craft: '{description}'")
    click.echo("(Craft output should be interpreted by Claude to generate a solution file)")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/cli.py tests/test_cli.py
git commit -m "feat: full engine CLI with all MVP commands"
```

---

### Task 8: End-to-End Test — Init → Look → Solve Flow

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write end-to-end test**

```python
# tests/test_e2e.py
"""End-to-end test: init → look → solve a puzzle."""
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from lifesim.cli import engine, main


class TestEndToEnd:
    def test_full_game_flow(self, tmp_path: Path, presets_dir: Path):
        runner = CliRunner()
        game_dir = tmp_path / "test-adventure"

        # 1. Create a new adventure
        with patch("lifesim.cli._find_presets_dir", return_value=presets_dir):
            result = runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "story"])
        assert result.exit_code == 0, result.output
        assert (game_dir / "CLAUDE.md").exists()

        env = {"LIFESIM_GAME_DIR": str(game_dir)}

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

        with patch("lifesim.cli._find_presets_dir", return_value=presets_dir):
            runner.invoke(main, ["new", str(game_dir), "--preset", "fantasy", "--mode", "technical"])

        env = {"LIFESIM_GAME_DIR": str(game_dir)}

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
```

- [ ] **Step 2: Run the end-to-end test**

```bash
pytest tests/test_e2e.py -v --tb=short
```

Expected: Both tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests across all files PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: end-to-end test for init → look → solve flow"
```

---

### Task 9: Polish & README

**Files:**
- Create: `README.md`
- Possible fixes to any issues found in full test run

- [ ] **Step 1: Create README**

```markdown
# LifeSim

An LLM-powered text RPG engine. Explore procedurally generated worlds, solve narrative-framed puzzles, and command AI companions — all from Claude Code.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Create an adventure
lifesim new my-adventure --preset fantasy --mode story

# Play
cd my-adventure
# Open in Claude Code — Claude reads CLAUDE.md and starts narrating
```

## Modes

- **Story mode**: Pure narrative experience. Describe your logic in natural language.
- **Technical mode**: See the code. Write solutions directly.

## How It Works

The game is a folder. Claude Code reads `CLAUDE.md` and acts as your narrator, calling `engine` commands to manage game state. Puzzles are backed by real Python validators. Your companions map to AI subagents.

```
my-adventure/
├── CLAUDE.md          # Claude's game master instructions
├── world/             # Generated terrain (zones, puzzles, NPCs)
├── player/            # Your state (inventory, companions, profile)
```

## Engine Commands

```bash
engine status          # Where am I?
engine look            # What do I see?
engine paths           # Where can I go?
engine move <zone>     # Go somewhere
engine puzzle          # What's the puzzle here?
engine solve <id> --solution <file>   # Submit a solution
engine hint <id>       # Get a hint
engine scout <dir>     # Scout companion scans ahead
engine research <topic> # Scholar companion investigates
engine craft <desc>    # Tinker companion builds
engine map             # Show explored world
engine companions      # List your party
engine inventory       # Check your items
engine profile         # See how the game adapts to you
```

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable (for terrain generation)
- Claude Code (for playing)
```

- [ ] **Step 2: Verify the full project runs clean**

```bash
cd /path/to/agentic-quest
source .venv/bin/activate
pytest tests/ -v --tb=short
lifesim --help
engine --help
```

Expected: All tests pass, both CLI commands show help.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start and engine command reference"
```

---

## Task Dependency Summary

```
Task 1 (scaffolding)
  ├── Task 2 (GameState) 
  │     └── Task 7 (CLI) ─── Task 8 (E2E)
  ├── Task 3 (Validator) ──┘
  ├── Task 4 (Profile) ────┘
  ├── Task 5 (Generator + Presets) ──┘
  └── Task 6 (Initializer + CLAUDE.md) ──┘
                                          └── Task 9 (Polish)
```

Tasks 2, 3, 4 can run in parallel after Task 1.
Task 5 depends on preset files but can parallelize with 2/3/4 for the Python code.
Task 6 depends on Task 4 (imports PlayerProfile).
Task 7 depends on Tasks 2, 3, 4.
Task 8 depends on Task 6, 7.
Task 9 depends on Task 8.
