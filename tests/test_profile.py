"""Tests for PlayerProfile."""
from pathlib import Path

import yaml

from agentic_quest.profile import PlayerProfile


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
        for i in range(3):
            profile.record_puzzle_attempt(f"p{i}", solved=True)
        assert profile.data["generation_hints"]["difficulty_target"] > 1.0

    def test_difficulty_adjusts_on_struggles(self, tmp_game_dir: Path):
        profile = PlayerProfile(tmp_game_dir / "player")
        profile.data["generation_hints"]["difficulty_target"] = 3.0
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
