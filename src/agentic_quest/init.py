"""Game initializer — scaffolds a new adventure from a preset."""
import json
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

    def create(self, game_dir: Path, preset: str, mode: str, source_text: str | None = None):
        game_dir = Path(game_dir)
        preset_dir = self.presets_dir / preset

        if not preset_dir.exists():
            raise FileNotFoundError(f"Preset not found: {preset}")

        game_dir.mkdir(parents=True, exist_ok=True)
        (game_dir / "world").mkdir(exist_ok=True)
        (game_dir / "player").mkdir(exist_ok=True)
        (game_dir / "player" / "companions").mkdir(exist_ok=True)

        preset_meta = yaml.safe_load((preset_dir / "preset.yaml").read_text())

        # Save source material if provided (used by generation prompts)
        if source_text:
            (game_dir / "world" / "source.md").write_text(source_text)

        # Copy starter zone (only if no source — source-based worlds generate their starter)
        if not source_text:
            starter_dir = preset_dir / "starter"
            if starter_dir.exists():
                for zone_dir in starter_dir.iterdir():
                    if zone_dir.is_dir():
                        shutil.copytree(zone_dir, game_dir / "world" / zone_dir.name, dirs_exist_ok=True)

        # Copy companion files (default companions, source-based games can override later)
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
            "has_source": source_text is not None,
        }
        (game_dir / "world" / "_meta.yaml").write_text(yaml.dump(meta, default_flow_style=False))

        # Create player state — use "start" as placeholder zone for source-based worlds
        starter_zone = "start" if source_text else preset_meta.get("starter_zone", "crossroads")
        player_state = {
            "name": "Adventurer",
            "location": starter_zone,
            "inventory": [],
            "companions": ["scout"],
            "puzzles_solved": [],
            "zones_visited": [starter_zone],
        }
        (game_dir / "player" / "state.yaml").write_text(yaml.dump(player_state, default_flow_style=False))

        # Create initial profile
        from agentic_quest.profile import PlayerProfile
        profile = PlayerProfile(game_dir / "player")
        profile.save()

        # Create agent-specific settings and instructions
        self._create_claude_settings(game_dir)
        self._create_codex_settings(game_dir)
        self._generate_instructions(game_dir, preset_dir, preset_meta, mode, source_text=source_text)

    def _create_claude_settings(self, game_dir: Path):
        claude_dir = game_dir / ".claude"
        claude_dir.mkdir(exist_ok=True)
        settings = {
            "permissions": {
                "allow": [
                    "Bash(engine *)",
                    "Bash(engine)",
                ]
            }
        }
        (claude_dir / "settings.json").write_text(
            json.dumps(settings, indent=2) + "\n"
        )

    def _create_codex_settings(self, game_dir: Path):
        """Create Codex config that auto-approves engine commands."""
        codex_dir = game_dir / ".codex"
        codex_dir.mkdir(exist_ok=True)
        config_toml = (
            '# Agentic Quest — Codex settings\n'
            'approval_policy = "on-request"\n'
            'sandbox_mode = "workspace-write"\n'
        )
        (codex_dir / "config.toml").write_text(config_toml)

    def _generate_instructions(
        self, game_dir: Path, preset_dir: Path, preset_meta: dict, mode: str,
        source_text: str | None = None,
    ):
        voice_guide = ""
        voice_path = preset_dir / "voice.md"
        if voice_path.exists():
            voice_guide = voice_path.read_text()

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
        instructions = template.render(
            preset_name=preset_meta.get("name", "Fantasy"),
            genre=preset_meta.get("name", "fantasy").lower(),
            mode=mode,
            voice_guide=voice_guide,
            companions=companions,
            source_material=source_text,
        )

        # Write for both Claude Code and Codex
        (game_dir / "CLAUDE.md").write_text(instructions)
        (game_dir / "AGENTS.md").write_text(instructions)
