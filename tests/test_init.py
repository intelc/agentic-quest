"""Tests for GameInitializer."""
import json
from pathlib import Path

import yaml

from agentic_quest.init import GameInitializer


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
        # AGENTS.md should also be created (for Codex)
        agents_md = (game_dir / "AGENTS.md").read_text()
        assert agents_md == claude_md

    def test_technical_mode_claude_md(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="technical")
        claude_md = (game_dir / "CLAUDE.md").read_text()
        assert "technical" in claude_md.lower() or "TECHNICAL" in claude_md

    def test_creates_claude_settings_with_engine_permissions(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")
        settings_path = game_dir / ".claude" / "settings.json"
        assert settings_path.exists()
        settings = json.loads(settings_path.read_text())
        assert "Bash(engine *)" in settings["permissions"]["allow"]
        assert "Bash(engine)" in settings["permissions"]["allow"]

    def test_copies_companion_files(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "my-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story")
        companions_dir = game_dir / "player" / "companions"
        assert (companions_dir / "scout.yaml").exists()
        assert (companions_dir / "scholar.yaml").exists()
        assert (companions_dir / "tinker.yaml").exists()
        assert (companions_dir / "cartographer.yaml").exists()


class TestSourceBasedWorld:
    def test_creates_world_from_source(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "wuxia-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        source = "在一座被云雾缭绕的山巅上，有一座古老的武当道观。少年张三丰正在练剑。"
        init.create(game_dir, preset="fantasy", mode="story", source_text=source)

        # Source saved to world/
        assert (game_dir / "world" / "source.md").exists()
        assert "张三丰" in (game_dir / "world" / "source.md").read_text()

        # No hardcoded starter zone (source-based generates its own)
        assert not (game_dir / "world" / "crossroads").exists()

        # Player starts at "start" placeholder
        player = yaml.safe_load((game_dir / "player" / "state.yaml").read_text())
        assert player["location"] == "start"

        # Meta tracks source
        meta = yaml.safe_load((game_dir / "world" / "_meta.yaml").read_text())
        assert meta["has_source"] is True

        # CLAUDE.md includes source material
        claude_md = (game_dir / "CLAUDE.md").read_text()
        assert "张三丰" in claude_md
        assert "source material" in claude_md.lower()

    def test_no_source_still_works(self, tmp_path: Path, presets_dir: Path):
        game_dir = tmp_path / "normal-adventure"
        init = GameInitializer(presets_dir=presets_dir)
        init.create(game_dir, preset="fantasy", mode="story", source_text=None)

        # Normal flow — hardcoded starter zone exists
        assert (game_dir / "world" / "crossroads").exists()
        assert not (game_dir / "world" / "source.md").exists()
