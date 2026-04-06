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

    # --- NPCs ---

    _MAX_NPC_EVENTS = 10

    def get_npc(self, zone_id: str, npc_id: str) -> dict | None:
        npc_path = self.game_dir / "world" / zone_id / npc_id / "npc.yaml"
        if not npc_path.exists():
            return None
        return yaml.safe_load(npc_path.read_text())

    def record_npc_event(self, zone_id: str, npc_id: str, description: str, zone: str | None = None):
        npc_path = self.game_dir / "world" / zone_id / npc_id / "npc.yaml"
        if not npc_path.exists():
            return
        npc = yaml.safe_load(npc_path.read_text())
        events = npc.setdefault("events", [])
        move_number = len(self.player.get("zones_visited", []))
        events.append({
            "description": description,
            "zone": zone or zone_id,
            "move_number": move_number,
        })
        if len(events) > self._MAX_NPC_EVENTS:
            npc["events"] = events[-self._MAX_NPC_EVENTS:]
        npc_path.write_text(yaml.dump(npc, default_flow_style=False))

    def get_npc_events_at(self, zone_id: str, npc_id: str, perspective_zone: str | None = None) -> list[dict]:
        npc = self.get_npc(zone_id, npc_id)
        if not npc or "events" not in npc:
            return []
        events = npc["events"]
        if perspective_zone is None:
            return events
        return [e for e in events if e.get("zone") == perspective_zone]
