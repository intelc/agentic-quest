"""Consequence manager — scheduled events that fire after N moves."""
import json
from pathlib import Path


class ConsequenceManager:
    """Manages scheduled future events with move-based timers."""

    def __init__(self, game_dir: Path):
        self.game_dir = Path(game_dir)
        self._path = self.game_dir / "world" / "consequences.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {"pending": [], "history": []}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2) + "\n")

    def schedule(
        self,
        description: str,
        trigger_after_moves: int,
        zone: str | None = None,
        event_type: str = "narrative_event",
    ):
        consequence = {
            "description": description,
            "moves_remaining": trigger_after_moves,
            "type": event_type,
        }
        if zone:
            consequence["zone"] = zone
        self._data["pending"].append(consequence)
        self._save()

    def tick(self) -> list[dict]:
        fired = []
        still_pending = []
        for c in self._data["pending"]:
            c["moves_remaining"] -= 1
            if c["moves_remaining"] <= 0:
                fired.append(c)
                self._data["history"].append(c)
            else:
                still_pending.append(c)
        self._data["pending"] = still_pending
        self._save()
        return fired

    def pending(self) -> list[dict]:
        return self._data["pending"]

    def history(self) -> list[dict]:
        return self._data["history"]
