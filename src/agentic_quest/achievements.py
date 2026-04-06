"""Achievement engine — evaluates deterministic triggers against player state."""
import json
from pathlib import Path

import yaml


class AchievementEngine:
    """Evaluates achievements from preset definitions against current player state."""

    def __init__(self, game_dir: Path, preset_dir: Path):
        self.game_dir = Path(game_dir)
        self._progress_path = self.game_dir / "player" / "achievements.json"
        self._progress = self._load_progress()

        defs_path = preset_dir / "achievements.json"
        self.definitions = json.loads(defs_path.read_text()) if defs_path.exists() else []

    def _load_progress(self) -> dict:
        if self._progress_path.exists():
            return json.loads(self._progress_path.read_text())
        return {"unlocked": [], "total_xp": 0}

    def _save_progress(self):
        self._progress_path.parent.mkdir(parents=True, exist_ok=True)
        self._progress_path.write_text(json.dumps(self._progress, indent=2) + "\n")

    def _load_player(self) -> dict:
        path = self.game_dir / "player" / "state.yaml"
        return yaml.safe_load(path.read_text()) if path.exists() else {}

    def unlocked(self) -> list[dict]:
        return self._progress["unlocked"]

    def total_xp(self) -> int:
        return self._progress["total_xp"]

    def check(self) -> list[dict]:
        player = self._load_player()
        unlocked_ids = {a["id"] for a in self._progress["unlocked"]}
        newly_unlocked = []

        for defn in self.definitions:
            if defn["id"] in unlocked_ids:
                continue
            if self._evaluate_trigger(defn["trigger"], player):
                entry = {"id": defn["id"], "name": defn["name"], "xp": defn["xp"]}
                self._progress["unlocked"].append(entry)
                self._progress["total_xp"] += defn["xp"]
                newly_unlocked.append(entry)

        if newly_unlocked:
            self._save_progress()
        return newly_unlocked

    def _evaluate_trigger(self, trigger: dict, player: dict) -> bool:
        t = trigger["type"]
        min_val = trigger.get("min", 1)

        if t == "zones_visited":
            return len(player.get("zones_visited", [])) >= min_val
        elif t == "puzzles_solved":
            return len(player.get("puzzles_solved", [])) >= min_val
        elif t == "items_collected":
            return len(player.get("inventory", [])) >= min_val
        elif t == "companions_recruited":
            return len(player.get("companions", [])) >= min_val
        elif t == "hints_used":
            return sum(player.get("hints_used", {}).values()) >= min_val
        return False

    def next_recommendations(self, limit: int = 3) -> list[dict]:
        unlocked_ids = {a["id"] for a in self._progress["unlocked"]}
        locked = [d for d in self.definitions if d["id"] not in unlocked_ids]
        rarity_order = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
        locked.sort(key=lambda d: rarity_order.get(d.get("rarity", "common"), 5))
        return locked[:limit]
