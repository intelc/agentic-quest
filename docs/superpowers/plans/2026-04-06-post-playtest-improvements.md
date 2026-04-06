# Post-Playtest Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 8 improvements from 3 playtests + competitive analysis: NPC memory, consequence system, engine context command, output templates, persist-before-narrate, perspective filtering, freeform triggers, and achievement system.

**Architecture:** Adds two new modules (`consequences.py`, `achievements.py`), extends `state.py` with NPC event tracking, adds `engine context`/`engine schedule`/`engine consequences`/`engine record-event`/`engine achievements`/`engine check-achievements` commands, and updates CLAUDE.md template with output templates, persist-before-narrate rules, and freeform trigger instructions.

**Tech Stack:** Python 3.11+, Click, PyYAML, pytest (existing stack — no new dependencies)

---

## File Structure

```
src/lifesim/
├── state.py              # MODIFY: add NPC event recording + perspective filtering
├── consequences.py       # CREATE: consequence/scheduled event manager
├── achievements.py       # CREATE: achievement evaluation engine
├── cli.py                # MODIFY: add 6 new engine commands
templates/
└── CLAUDE.md.j2          # MODIFY: output templates, persist-before-narrate, freeform rules
presets/fantasy/
└── achievements.json     # CREATE: fantasy preset achievement definitions
tests/
├── conftest.py           # MODIFY: add NPC events fixture
├── test_state.py         # MODIFY: add NPC event tests
├── test_consequences.py  # CREATE
├── test_achievements.py  # CREATE
└── test_cli.py           # MODIFY: add tests for new commands
```

---

### Task 1: NPC Event Memory (Improvements 2 + 6)

**Files:**
- Modify: `src/lifesim/state.py`
- Modify: `tests/test_state.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing tests for NPC event recording and filtering**

```python
# Add to tests/test_state.py

class TestNpcEvents:
    def test_record_event(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Sold a compass to the player")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc.get("events", [])) == 1
        assert npc["events"][0]["description"] == "Sold a compass to the player"
        assert "zone" in npc["events"][0]
        assert "move_number" in npc["events"][0]

    def test_record_multiple_events(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Greeted the player")
        gs.record_npc_event("crossroads", "old_merchant", "Gave a hint about the signpost")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc["events"]) == 2

    def test_get_npc(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        npc = gs.get_npc("crossroads", "old_merchant")
        assert npc["name"] == "Old Merchant"
        assert "dialogue" in npc

    def test_get_npc_missing(self, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        assert gs.get_npc("crossroads", "nobody") is None

    def test_get_npc_events_filtered_by_zone(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Saw the player solve the puzzle", zone="crossroads")
        gs.record_npc_event("crossroads", "old_merchant", "Heard a distant rumble", zone="dark_forest")
        # Merchant is in crossroads — should only see crossroads events
        events = gs.get_npc_events_at("crossroads", "old_merchant", perspective_zone="crossroads")
        assert len(events) == 1
        assert events[0]["description"] == "Saw the player solve the puzzle"

    def test_companion_sees_all_events(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        gs.record_npc_event("crossroads", "old_merchant", "Event in crossroads", zone="crossroads")
        gs.record_npc_event("crossroads", "old_merchant", "Event in forest", zone="dark_forest")
        # Companions see all events (they travel with the player)
        events = gs.get_npc_events_at("crossroads", "old_merchant", perspective_zone=None)
        assert len(events) == 2

    def test_events_capped_at_max(self, sample_zone_dir: Path, tmp_game_dir: Path):
        gs = GameState(tmp_game_dir)
        for i in range(15):
            gs.record_npc_event("crossroads", "old_merchant", f"Event {i}")
        npc = gs.get_npc("crossroads", "old_merchant")
        assert len(npc["events"]) == 10  # capped at 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/agentic-quest
source .venv/bin/activate
pytest tests/test_state.py::TestNpcEvents -v --tb=short
```

Expected: FAIL (methods don't exist)

- [ ] **Step 3: Implement NPC event methods in GameState**

Add these methods to `src/lifesim/state.py` in the `GameState` class:

```python
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
        # Cap at max events (keep most recent)
        if len(events) > self._MAX_NPC_EVENTS:
            npc["events"] = events[-self._MAX_NPC_EVENTS:]
        npc_path.write_text(yaml.dump(npc, default_flow_style=False))

    def get_npc_events_at(self, zone_id: str, npc_id: str, perspective_zone: str | None = None) -> list[dict]:
        npc = self.get_npc(zone_id, npc_id)
        if not npc or "events" not in npc:
            return []
        events = npc["events"]
        if perspective_zone is None:
            return events  # companions see all
        return [e for e in events if e.get("zone") == perspective_zone]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v --tb=short
```

Expected: All tests PASS (both old and new).

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/state.py tests/test_state.py
git commit -m "feat: NPC event memory with perspective filtering"
```

---

### Task 2: Consequence / Scheduled Events System (Improvement 3)

**Files:**
- Create: `src/lifesim/consequences.py`
- Create: `tests/test_consequences.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_consequences.py
"""Tests for ConsequenceManager."""
from pathlib import Path

import yaml

from lifesim.consequences import ConsequenceManager


class TestConsequenceManager:
    def test_loads_empty(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        assert cm.pending() == []

    def test_schedule_consequence(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("A stranger arrives at the crossroads", trigger_after_moves=3)
        assert len(cm.pending()) == 1
        assert cm.pending()[0]["description"] == "A stranger arrives at the crossroads"
        assert cm.pending()[0]["moves_remaining"] == 3

    def test_schedule_with_zone(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Bridge collapses", trigger_after_moves=2, zone="river_valley")
        assert cm.pending()[0]["zone"] == "river_valley"

    def test_schedule_with_type(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("New path opens", trigger_after_moves=1, event_type="path_opens")
        assert cm.pending()[0]["type"] == "path_opens"

    def test_tick_decrements_moves(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Something happens", trigger_after_moves=3)
        fired = cm.tick()
        assert fired == []
        assert cm.pending()[0]["moves_remaining"] == 2

    def test_tick_fires_at_zero(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Something happens", trigger_after_moves=1)
        fired = cm.tick()
        assert len(fired) == 1
        assert fired[0]["description"] == "Something happens"
        assert cm.pending() == []  # removed from pending

    def test_tick_fires_multiple(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("First", trigger_after_moves=1)
        cm.schedule("Second", trigger_after_moves=1)
        cm.schedule("Third", trigger_after_moves=3)
        fired = cm.tick()
        assert len(fired) == 2
        assert len(cm.pending()) == 1

    def test_persists_to_disk(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Persistent event", trigger_after_moves=5)
        # Reload from disk
        cm2 = ConsequenceManager(tmp_game_dir)
        assert len(cm2.pending()) == 1
        assert cm2.pending()[0]["description"] == "Persistent event"

    def test_fired_events_saved_to_history(self, tmp_game_dir: Path):
        cm = ConsequenceManager(tmp_game_dir)
        cm.schedule("Past event", trigger_after_moves=1)
        cm.tick()
        assert len(cm.history()) == 1
        assert cm.history()[0]["description"] == "Past event"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_consequences.py -v --tb=short
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement ConsequenceManager**

```python
# src/lifesim/consequences.py
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
        """Decrement all timers by 1. Return and remove any that hit 0."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_consequences.py -v --tb=short
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/consequences.py tests/test_consequences.py
git commit -m "feat: ConsequenceManager for scheduled events with move-based timers"
```

---

### Task 3: Achievement System (Improvement 8)

**Files:**
- Create: `src/lifesim/achievements.py`
- Create: `presets/fantasy/achievements.json`
- Create: `tests/test_achievements.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_achievements.py
"""Tests for AchievementEngine."""
from pathlib import Path

import json
import yaml

from lifesim.achievements import AchievementEngine


class TestAchievementEngine:
    def test_loads_definitions(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        assert len(ae.definitions) > 0

    def test_no_achievements_initially(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        assert ae.unlocked() == []

    def test_check_zones_visited(self, tmp_game_dir: Path, presets_dir: Path):
        # Set up player with 3 zones visited
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        newly_unlocked = ae.check()
        explorer = [a for a in newly_unlocked if a["id"] == "first_steps"]
        assert len(explorer) == 1

    def test_check_puzzle_solved(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        newly_unlocked = ae.check()
        puzzle_ids = [a["id"] for a in newly_unlocked]
        assert "puzzle_novice" in puzzle_ids

    def test_doesnt_double_unlock(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        first = ae.check()
        second = ae.check()
        assert len(second) == 0  # already unlocked

    def test_total_xp(self, tmp_game_dir: Path, presets_dir: Path):
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["puzzles_solved"] = ["broken_signpost"]
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        ae.check()
        assert ae.total_xp() > 0

    def test_next_recommendations(self, tmp_game_dir: Path, presets_dir: Path):
        ae = AchievementEngine(tmp_game_dir, presets_dir / "fantasy")
        recs = ae.next_recommendations(limit=3)
        assert len(recs) <= 3
        assert all("name" in r for r in recs)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_achievements.py -v --tb=short
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create fantasy achievement definitions**

```json
[
    {
        "id": "first_steps",
        "name": "First Steps",
        "description": "Visit 3 different zones",
        "category": "exploration",
        "xp": 10,
        "rarity": "common",
        "trigger": {"type": "zones_visited", "min": 3}
    },
    {
        "id": "wanderer",
        "name": "Wanderer",
        "description": "Visit 7 different zones",
        "category": "exploration",
        "xp": 50,
        "rarity": "rare",
        "trigger": {"type": "zones_visited", "min": 7}
    },
    {
        "id": "puzzle_novice",
        "name": "Puzzle Novice",
        "description": "Solve your first puzzle",
        "category": "puzzle",
        "xp": 10,
        "rarity": "common",
        "trigger": {"type": "puzzles_solved", "min": 1}
    },
    {
        "id": "puzzle_adept",
        "name": "Puzzle Adept",
        "description": "Solve 5 puzzles",
        "category": "puzzle",
        "xp": 50,
        "rarity": "rare",
        "trigger": {"type": "puzzles_solved", "min": 5}
    },
    {
        "id": "social_butterfly",
        "name": "Social Butterfly",
        "description": "Collect 3 items from NPCs",
        "category": "social",
        "xp": 25,
        "rarity": "uncommon",
        "trigger": {"type": "items_collected", "min": 3}
    },
    {
        "id": "well_equipped",
        "name": "Well Equipped",
        "description": "Collect 5 items",
        "category": "discovery",
        "xp": 25,
        "rarity": "uncommon",
        "trigger": {"type": "items_collected", "min": 5}
    },
    {
        "id": "party_leader",
        "name": "Party Leader",
        "description": "Recruit 3 companions",
        "category": "social",
        "xp": 50,
        "rarity": "rare",
        "trigger": {"type": "companions_recruited", "min": 3}
    },
    {
        "id": "first_hint",
        "name": "Asking for Directions",
        "description": "Use a hint for the first time",
        "category": "puzzle",
        "xp": 10,
        "rarity": "common",
        "trigger": {"type": "hints_used", "min": 1}
    }
]
```

Save to `presets/fantasy/achievements.json`.

- [ ] **Step 4: Implement AchievementEngine**

```python
# src/lifesim/achievements.py
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
        """Evaluate all triggers, unlock new achievements. Returns newly unlocked."""
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
        """Return up to `limit` locked achievements closest to being unlocked."""
        unlocked_ids = {a["id"] for a in self._progress["unlocked"]}
        locked = [d for d in self.definitions if d["id"] not in unlocked_ids]
        # Sort by rarity (common first = easier)
        rarity_order = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
        locked.sort(key=lambda d: rarity_order.get(d.get("rarity", "common"), 5))
        return locked[:limit]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_achievements.py -v --tb=short
```

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/lifesim/achievements.py presets/fantasy/achievements.json tests/test_achievements.py
git commit -m "feat: achievement system with deterministic triggers and fantasy definitions"
```

---

### Task 4: Engine Context Command (Improvement 5)

**Files:**
- Modify: `src/lifesim/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_cli.py

class TestEngineContext:
    def test_returns_aggregated_state(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(engine, ["context"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        # Should contain player info
        assert "Testplayer" in result.output
        assert "crossroads" in result.output.lower()
        # Should contain zone narrative
        assert "signpost" in result.output.lower() or "merchant" in result.output.lower()
        # Should contain paths
        assert "dark_forest" in result.output.lower() or "Dark Forest" in result.output
        # Should contain puzzle info
        assert "Broken Signpost" in result.output or "broken_signpost" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py::TestEngineContext -v --tb=short
```

Expected: FAIL (command doesn't exist)

- [ ] **Step 3: Implement engine context command**

Add to `src/lifesim/cli.py`:

```python
@engine.command()
def context():
    """Aggregated game context for session start (replaces status+look+paths+puzzle)."""
    gs = _load_state()
    location = gs.player["location"]
    zone = gs.get_zone(location)
    narrative = gs.get_zone_narrative(location)

    # Player state
    click.echo("=== PLAYER ===")
    click.echo(f"Name: {gs.player.get('name', 'Unknown')}")
    click.echo(f"Location: {location}")
    click.echo(f"Companions: {', '.join(gs.player.get('companions', []))}")
    click.echo(f"Inventory: {', '.join(gs.player.get('inventory', [])) or 'empty'}")
    click.echo(f"Puzzles solved: {', '.join(gs.player.get('puzzles_solved', [])) or 'none'}")

    # Zone narrative
    click.echo(f"\n=== ZONE: {zone['name'] if zone else location} ===")
    if narrative:
        click.echo(narrative)

    # NPCs
    if zone and zone.get("npcs"):
        click.echo(f"\n=== NPCs ===")
        for npc_id in zone["npcs"]:
            npc = gs.get_npc(location, npc_id)
            if npc:
                click.echo(f"  {npc.get('name', npc_id)}: {npc.get('description', '')}")
                events = npc.get("events", [])
                if events:
                    click.echo(f"    Recent: {events[-1]['description']}")

    # Paths
    zone_paths = gs.get_paths(location)
    if zone_paths:
        click.echo(f"\n=== PATHS ===")
        for p in zone_paths:
            click.echo(f"  {p['id']}: {p['name']} [{p.get('status', '?')}] — {p.get('teaser', '')}")

    # Puzzles
    if zone and zone.get("puzzles"):
        click.echo(f"\n=== PUZZLES ===")
        for puzzle_id in zone["puzzles"]:
            p = gs.get_puzzle(location, puzzle_id)
            if p:
                solved = " [SOLVED]" if p.get("solved") else ""
                click.echo(f"  {p['name']}{solved} (ID: {puzzle_id}, difficulty: {p.get('difficulty', '?')})")

    # Consequences
    from lifesim.consequences import ConsequenceManager
    cm = ConsequenceManager(gs.game_dir)
    pending = cm.pending()
    if pending:
        click.echo(f"\n=== PENDING EVENTS ({len(pending)}) ===")
        for c in pending:
            click.echo(f"  [{c['moves_remaining']} moves] {c['description']}")

    # Profile summary
    prof = PlayerProfile(gs.game_dir / "player")
    click.echo(f"\n=== PROFILE ===")
    click.echo(f"Difficulty: {prof.data['generation_hints']['difficulty_target']:.1f}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lifesim/cli.py tests/test_cli.py
git commit -m "feat: engine context command — aggregated state for session start"
```

---

### Task 5: CLI Commands for Consequences, NPC Events, Achievements

**Files:**
- Modify: `src/lifesim/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_cli.py

class TestEngineRecordEvent:
    def test_records_npc_event(self, tmp_game_dir: Path, sample_zone_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["record-event", "old_merchant", "Sold a compass"],
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "recorded" in result.output.lower()


class TestEngineSchedule:
    def test_schedules_consequence(self, tmp_game_dir: Path):
        runner = CliRunner()
        result = runner.invoke(
            engine,
            ["schedule", "A stranger arrives", "--after", "3"],
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
        )
        assert result.exit_code == 0
        assert "scheduled" in result.output.lower()


class TestEngineConsequences:
    def test_shows_pending(self, tmp_game_dir: Path):
        runner = CliRunner()
        # Schedule something first
        runner.invoke(
            engine,
            ["schedule", "Storm coming", "--after", "2"],
            env={"LIFESIM_GAME_DIR": str(tmp_game_dir)},
        )
        result = runner.invoke(engine, ["consequences"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "Storm coming" in result.output


class TestEngineAchievements:
    def test_shows_achievements(self, tmp_game_dir: Path, presets_dir: Path):
        runner = CliRunner()
        # Need to set preset in meta so achievements can find definitions
        import yaml
        meta = yaml.safe_load((tmp_game_dir / "world" / "_meta.yaml").read_text())
        meta["preset"] = "fantasy"
        (tmp_game_dir / "world" / "_meta.yaml").write_text(yaml.dump(meta))

        result = runner.invoke(engine, ["achievements"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0

    def test_check_achievements(self, tmp_game_dir: Path, sample_zone_dir: Path, presets_dir: Path):
        runner = CliRunner()
        # Give player 3 zones visited to trigger first_steps
        import yaml
        state = yaml.safe_load((tmp_game_dir / "player" / "state.yaml").read_text())
        state["zones_visited"] = ["crossroads", "dark_forest", "river_valley"]
        (tmp_game_dir / "player" / "state.yaml").write_text(yaml.dump(state))

        result = runner.invoke(engine, ["check-achievements"], env={"LIFESIM_GAME_DIR": str(tmp_game_dir)})
        assert result.exit_code == 0
        assert "First Steps" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py::TestEngineRecordEvent tests/test_cli.py::TestEngineSchedule tests/test_cli.py::TestEngineConsequences tests/test_cli.py::TestEngineAchievements -v --tb=short
```

Expected: FAIL (commands don't exist)

- [ ] **Step 3: Implement the 5 new CLI commands**

Add to `src/lifesim/cli.py`:

```python
@engine.command("record-event")
@click.argument("npc_id")
@click.argument("description")
def record_event(npc_id: str, description: str):
    """Record an event in an NPC's memory."""
    gs = _load_state()
    location = gs.player["location"]
    gs.record_npc_event(location, npc_id, description, zone=location)
    click.echo(f"Event recorded for {npc_id}: {description}")


@engine.command()
@click.argument("description")
@click.option("--after", required=True, type=int, help="Trigger after N moves.")
@click.option("--zone", default=None, help="Zone where this triggers (optional).")
@click.option("--type", "event_type", default="narrative_event", help="Event type.")
def schedule(description: str, after: int, zone: str | None, event_type: str):
    """Schedule a future event that triggers after N moves."""
    from lifesim.consequences import ConsequenceManager
    gs = _load_state()
    cm = ConsequenceManager(gs.game_dir)
    cm.schedule(description, trigger_after_moves=after, zone=zone, event_type=event_type)
    click.echo(f"Scheduled: '{description}' (in {after} moves)")


@engine.command()
def consequences():
    """Show pending scheduled events."""
    gs = _load_state()
    from lifesim.consequences import ConsequenceManager
    cm = ConsequenceManager(gs.game_dir)
    pending = cm.pending()
    if not pending:
        click.echo("No pending events.")
        return
    click.echo("=== Pending Events ===\n")
    for c in pending:
        zone_str = f" [in {c['zone']}]" if c.get("zone") else ""
        click.echo(f"  [{c['moves_remaining']} moves] {c['description']}{zone_str}")


@engine.command()
def achievements():
    """Show unlocked achievements and recommendations."""
    gs = _load_state()
    preset_dir = _find_presets_dir() / gs.meta.get("preset", "fantasy")
    from lifesim.achievements import AchievementEngine
    ae = AchievementEngine(gs.game_dir, preset_dir)
    unlocked = ae.unlocked()
    click.echo(f"=== Achievements ({len(unlocked)} unlocked, {ae.total_xp()} XP) ===\n")
    for a in unlocked:
        click.echo(f"  ✓ {a['name']} (+{a['xp']} XP)")
    recs = ae.next_recommendations(3)
    if recs:
        click.echo(f"\n=== Next Goals ===")
        for r in recs:
            click.echo(f"  → {r['name']}: {r['description']}")


@engine.command("check-achievements")
def check_achievements():
    """Evaluate achievement triggers and unlock any newly earned."""
    gs = _load_state()
    preset_dir = _find_presets_dir() / gs.meta.get("preset", "fantasy")
    from lifesim.achievements import AchievementEngine
    ae = AchievementEngine(gs.game_dir, preset_dir)
    newly = ae.check()
    if newly:
        for a in newly:
            click.echo(f"ACHIEVEMENT UNLOCKED: {a['name']} (+{a['xp']} XP)")
    else:
        click.echo("No new achievements.")
    recs = ae.next_recommendations(3)
    if recs:
        click.echo(f"\nNext goals:")
        for r in recs:
            click.echo(f"  → {r['name']}: {r['description']}")
```

- [ ] **Step 4: Wire consequence ticking into the move command**

In the existing `move` command in `src/lifesim/cli.py`, add consequence ticking after the move succeeds. Find the line `click.echo(f"Moved to {zone['name']}.")` and add after it:

```python
    # Tick consequences on every move
    from lifesim.consequences import ConsequenceManager
    cm = ConsequenceManager(gs.game_dir)
    fired = cm.tick()
    for event in fired:
        click.echo(f"EVENT: {event['description']}")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/lifesim/cli.py tests/test_cli.py
git commit -m "feat: engine commands for record-event, schedule, consequences, achievements"
```

---

### Task 6: CLAUDE.md Template Updates (Improvements 1, 4, 7)

**Files:**
- Modify: `templates/CLAUDE.md.j2`

This task updates the CLAUDE.md template with persist-before-narrate rules, output templates, freeform trigger instructions, and references to all new engine commands.

- [ ] **Step 1: Add persist-before-narrate rule**

In the Important Rules section of `templates/CLAUDE.md.j2`, add as the SECOND rule (after "You are the narrator"):

```
- **PERSIST BEFORE NARRATE.** Always run engine mutation commands (move, solve, add-item, record-event, schedule) BEFORE narrating their result. If the session drops mid-response, the state is already saved.
```

- [ ] **Step 2: Add output templates section**

Add after the Proactive Engagement section:

```jinja2
## Output Templates

Use consistent formatting for each type of content:

**Scene (entering a zone):**
```
=== [Zone Name] ===

[2-3 paragraphs of second-person narrative]

[NPC reactions or environmental details]
```

**NPC Dialogue:**
```
**[NPC Name]** leans forward. "[Dialogue line.]"

*[Action or gesture description]*
```

**Puzzle Prompt:**
```
--- CHALLENGE: [Puzzle Name] ---

[Narrative description of the obstacle]

[What the player needs to figure out — framed as a question]
```

**Choice Menu:**
```
[Narrative hook or question]

[A] [Option] — [brief description]
[B] [Option] — [brief description]
[C] [Option] — [brief description]
[D] Something else (describe what you'd like to do)
```

**Achievement Unlocked:**
```
★ ACHIEVEMENT UNLOCKED: [Name] ★
[Description] (+[XP] XP)
```
```

- [ ] **Step 3: Add new commands to engine reference**

In the Engine Commands Reference section, add:

```bash
# NPC memory
engine record-event <npc_id> "<description>"  # Record event in NPC's memory
engine talk <npc_id>                          # Talk to NPC (includes their memory)

# Scheduled events
engine schedule "<description>" --after <N>   # Schedule event in N moves
engine consequences                           # Show pending events

# Achievements
engine check-achievements                     # Check for newly earned achievements
engine achievements                           # Show unlocked + next goals

# Aggregated context (use at session start instead of status+look+paths)
engine context                                # Everything in one call
```

- [ ] **Step 4: Update game loop to use new commands**

Replace the current game loop with:

```jinja2
## Game Loop

Every time a new session starts or the player returns:

1. Run `engine context` to get everything in one call
2. **Immediately dispatch a background subagent** to run `engine pregenerate`
3. Narrate where the player is and what they see
4. Use `engine say` to read the key narrative aloud
5. Present choices (lettered or freeform — see rules below)
6. After the player acts:
   - Run mutation commands FIRST (persist before narrate)
   - Run `engine record-event` for significant NPC interactions
   - Run `engine schedule` to set up future events when narratively appropriate
   - Run `engine check-achievements` after puzzle solves, zone transitions, or item pickups
   - THEN narrate the result
```

- [ ] **Step 5: Add freeform interaction type guidance**

In the Presenting Choices section, ensure the freeform block includes interaction types:

```
**Freeform interaction types to use:**
- **Describe** (puzzles): "How would you arrange these symbols? Explain your thinking."
- **Dialogue** (NPCs): "What do you say to the merchant?" — don't offer scripted lines
- **Create** (crafting/naming): "What do you want the Tinker to build?" or "Name your new weapon."
- **Imagine** (exploration): "You peer through the crystal. What do you see?"
- **Decide** (moral/strategic): "The path splits. No signs. Where does your gut say to go?"
```

- [ ] **Step 6: Verify template renders**

```bash
cd /path/to/agentic-quest
source .venv/bin/activate
python -c "
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import yaml

env = Environment(loader=FileSystemLoader('templates'), keep_trailing_newline=True)
template = env.get_template('CLAUDE.md.j2')
companions = []
for f in sorted(Path('presets/fantasy/companions').glob('*.yaml')):
    companions.append(yaml.safe_load(f.read_text()))
result = template.render(
    preset_name='Fantasy', genre='fantasy', mode='story',
    voice_guide='Test voice guide.', companions=companions,
)
print(f'Template rendered: {len(result)} chars')
assert 'PERSIST BEFORE NARRATE' in result
assert 'engine context' in result
assert 'engine record-event' in result
assert 'engine schedule' in result
assert 'engine check-achievements' in result
assert 'ACHIEVEMENT UNLOCKED' in result
print('All assertions passed.')
"
```

Expected: Template renders without errors, all new content present.

- [ ] **Step 7: Run full test suite (E2E tests use template)**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/CLAUDE.md.j2
git commit -m "feat: CLAUDE.md updates — persist-before-narrate, output templates, freeform types, new commands"
```

---

## Task Dependency Summary

```
Task 1 (NPC memory)        — independent
Task 2 (Consequences)      — independent  
Task 3 (Achievements)      — independent
Task 4 (engine context)    — depends on Task 1 + Task 2 (uses their data)
Task 5 (CLI commands)      — depends on Task 1 + Task 2 + Task 3
Task 6 (CLAUDE.md)         — depends on Task 4 + Task 5 (references new commands)
```

Tasks 1, 2, 3 can run in parallel.
Task 4 depends on 1 and 2.
Task 5 depends on 1, 2, and 3.
Task 6 depends on all others.
