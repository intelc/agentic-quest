"""Player profile — tracks behavior signals and adapts generation hints."""
from pathlib import Path

import yaml


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

            if self._total_puzzles_solved > 0:
                self.data["skill_signals"]["avg_attempts_per_puzzle"] = (
                    self._total_attempts / self._total_puzzles_solved
                )

            if puzzle_type:
                enjoyed = self.data["skill_signals"]["puzzle_types_enjoyed"]
                if puzzle_type not in enjoyed:
                    enjoyed.append(puzzle_type)

            if attempts_this_puzzle == 1:
                self.data["generation_hints"]["difficulty_target"] = min(
                    10.0,
                    self.data["generation_hints"]["difficulty_target"] + 0.3,
                )
        else:
            if self._total_puzzles_solved > 0:
                self.data["skill_signals"]["avg_attempts_per_puzzle"] = (
                    self._total_attempts / self._total_puzzles_solved
                )

            if self._puzzle_attempts[puzzle_id] >= 4:
                self.data["generation_hints"]["difficulty_target"] = max(
                    0.5,
                    self.data["generation_hints"]["difficulty_target"] - 0.2,
                )

    def save(self):
        self._path.write_text(yaml.dump(self.data, default_flow_style=False))


def _deep_copy_default() -> dict:
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
