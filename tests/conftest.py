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
