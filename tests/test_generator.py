# tests/test_generator.py
"""Tests for ZoneGenerator."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from agentic_quest.generator import ZoneGenerator


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
        assert len(rendered) > 50
