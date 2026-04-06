# src/lifesim/cli.py
"""CLI entry points for lifesim."""
import os
import re
from pathlib import Path

import click
import yaml

from agentic_quest.profile import PlayerProfile
from agentic_quest.state import GameState
from agentic_quest.validator import PuzzleValidator


def _find_presets_dir() -> Path:
    return Path(__file__).parent.parent.parent / "presets"


def _load_dotenv(game_dir: Path):
    """Load .env file from game directory or parent directories."""
    # Check game dir first, then walk up to find .env
    search_dir = game_dir
    for _ in range(5):  # max 5 levels up
        env_path = search_dir / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value:
                        os.environ.setdefault(key, value)
            return
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent


def _get_game_dir() -> Path:
    env_dir = os.environ.get("AQ_GAME_DIR")
    if env_dir:
        return Path(env_dir)
    cwd = Path.cwd()
    if (cwd / "world" / "_meta.yaml").exists():
        return cwd
    click.echo("Error: not in a game directory. Set AQ_GAME_DIR or cd into a game folder.", err=True)
    raise SystemExit(1)


def _is_eco_mode() -> bool:
    """Check if eco mode is enabled (uses Claude Code CLI instead of API key)."""
    return os.environ.get("ECO", "").lower() in ("on", "true", "1")


def _load_state() -> GameState:
    game_dir = _get_game_dir()
    _load_dotenv(game_dir)
    return GameState(game_dir)


def _sanitize_zone_id(description: str) -> str:
    """Convert a description into a clean zone ID slug. Supports CJK characters."""
    slug = description.lower().strip()
    # Keep alphanumeric, CJK unified ideographs, and whitespace
    slug = re.sub(r'[^\w\s]', '', slug, flags=re.UNICODE)
    slug = re.sub(r'\s+', '_', slug)
    slug = slug.strip('_')
    # Take first 3 meaningful parts, max 30 chars
    parts = slug.split('_')[:3]
    result = '_'.join(parts)[:30].rstrip('_')
    # Fallback if empty (shouldn't happen now but just in case)
    return result or f"zone_{hash(description) % 10000}"


@click.group()
def main():
    """Agentic Quest — drop into any fiction, solve puzzles, command AI companions."""
    pass


@main.command()
@click.argument("path")
@click.option("--preset", default="fantasy", help="World preset to use.")
@click.option("--mode", type=click.Choice(["story", "technical"]), default="story", help="Player mode.")
@click.option("--source", default=None, type=click.Path(exists=True), help="Fiction source file to build the world from.")
def new(path: str, preset: str, mode: str, source: str | None):
    """Create a new adventure. Optionally provide --source to build a world from fiction."""
    from agentic_quest.init import GameInitializer
    game_dir = Path(path)
    presets_dir = _find_presets_dir()
    source_text = None
    if source:
        source_text = Path(source).read_text()
        click.echo(f"Building world from source: {source} ({len(source_text)} chars)")
    init = GameInitializer(presets_dir=presets_dir)
    init.create(game_dir, preset=preset, mode=mode, source_text=source_text)
    click.echo(f"Adventure created at {game_dir}")
    click.echo("Open this folder in Claude Code to start playing!")


@click.group()
def engine():
    """In-game engine commands (called by Claude during gameplay)."""
    pass


@engine.command()
def status():
    """Show current game state summary."""
    gs = _load_state()
    click.echo(f"Player: {gs.player.get('name', 'Unknown')}")
    click.echo(f"Location: {gs.player['location']}")
    click.echo(f"Companions: {', '.join(gs.player.get('companions', []))}")
    click.echo(f"Inventory: {', '.join(gs.player.get('inventory', [])) or 'empty'}")
    click.echo(f"Puzzles solved: {', '.join(gs.player.get('puzzles_solved', [])) or 'none'}")
    click.echo(f"Zones visited: {', '.join(gs.player.get('zones_visited', []))}")


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
    from agentic_quest.consequences import ConsequenceManager
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


@engine.command()
def look():
    """Describe the current zone."""
    gs = _load_state()
    location = gs.player["location"]
    zone = gs.get_zone(location)
    narrative = gs.get_zone_narrative(location)
    if zone:
        click.echo(f"=== {zone['name']} ===\n")
    if narrative:
        click.echo(narrative)
    else:
        click.echo(f"You are at {location}. (No narrative available.)")
    if zone and zone.get("npcs"):
        click.echo(f"\nNPCs here: {', '.join(zone['npcs'])}")
    if zone and zone.get("puzzles"):
        for puzzle_id in zone["puzzles"]:
            puzzle = gs.get_puzzle(location, puzzle_id)
            if puzzle and not puzzle.get("solved"):
                click.echo(f"\nPuzzle: {puzzle['name']} (unsolved)")
            elif puzzle and puzzle.get("solved"):
                click.echo(f"\nPuzzle: {puzzle['name']} (solved)")


@engine.command()
def paths():
    """Show available paths from current zone."""
    gs = _load_state()
    location = gs.player["location"]
    zone_paths = gs.get_paths(location)
    if not zone_paths:
        click.echo("No paths visible from here.")
        return
    click.echo("Available paths:\n")
    for p in zone_paths:
        status = p.get("status", "unknown")
        teaser = p.get("teaser", "")
        click.echo(f"  {p['id']}: {p['name']} [{status}] — {teaser}")


@engine.command()
@click.argument("zone_id")
def move(zone_id: str):
    """Move to a zone. Auto-generates it if it's a known but ungenerated connection."""
    gs = _load_state()
    zone = gs.get_zone(zone_id)

    # If zone doesn't exist yet, check if it's a known connection and auto-generate
    if not zone:
        current_zone = gs.get_zone(gs.player["location"])
        connections = current_zone.get("connections", {}) if current_zone else {}
        if zone_id in connections:
            click.echo(f"Generating {connections[zone_id].get('name', zone_id)}...")
            meta = gs.meta
            eco = _is_eco_mode()
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not eco and not api_key:
                click.echo("Error: ANTHROPIC_API_KEY not set.", err=True)
                return
            from agentic_quest.generator import ZoneGenerator
            preset_dir = _find_presets_dir() / meta.get("preset", "fantasy")
            gen = ZoneGenerator(game_dir=gs.game_dir, preset_dir=preset_dir, api_key=api_key, eco=eco)
            profile = PlayerProfile(gs.game_dir / "player")
            context = {
                "adjacent_zones": [gs.player["location"]],
                "player_profile": profile.data,
                "difficulty": profile.data["generation_hints"]["difficulty_target"],
                "pacing": "exploration",
                "world_seed": meta.get("seed", 42),
                "inventory": gs.player.get("inventory", []),
                "open_puzzles": [],
            }
            gen.generate_full_zone(zone_id, context)
            zone = gs.get_zone(zone_id)

    if not zone:
        click.echo(f"Zone '{zone_id}' not found. Use 'engine generate' to create a new zone.")
        return

    gs.move_player(zone_id)
    visited = gs.player.setdefault("zones_visited", [])
    if zone_id not in visited:
        visited.append(zone_id)
        gs._save_player()
    click.echo(f"Moved to {zone['name']}.")

    # Tick consequences on every move
    from agentic_quest.consequences import ConsequenceManager
    cm = ConsequenceManager(gs.game_dir)
    fired = cm.tick()
    for event in fired:
        click.echo(f"EVENT: {event['description']}")


@engine.command()
@click.argument("description")
def generate(description: str):
    """Generate a new zone (for unexpected player actions)."""
    gs = _load_state()
    meta = gs.meta
    eco = _is_eco_mode()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not eco and not api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set. Set it or enable eco mode (ECO=on).", err=True)
        raise SystemExit(1)
    from agentic_quest.generator import ZoneGenerator
    preset_dir = _find_presets_dir() / meta.get("preset", "fantasy")
    gen = ZoneGenerator(game_dir=gs.game_dir, preset_dir=preset_dir, api_key=api_key, eco=eco)
    location = gs.player["location"]
    profile = PlayerProfile(gs.game_dir / "player")
    context = {
        "adjacent_zones": gs.player.get("zones_visited", []),
        "player_profile": profile.data,
        "difficulty": profile.data["generation_hints"]["difficulty_target"],
        "pacing": "exploration",
        "world_seed": meta.get("seed", 42),
        "inventory": gs.player.get("inventory", []),
        "open_puzzles": [],
    }
    zone_id = _sanitize_zone_id(description)
    click.echo(f"Generating zone '{zone_id}'...")
    gen.generate_full_zone(zone_id, context)
    current_zone = gs.get_zone(location)
    if current_zone:
        connections = current_zone.setdefault("connections", {})
        connections[zone_id] = {"name": description, "teaser": "A newly discovered area.", "status": "explored"}
        zone_path = gs.game_dir / "world" / location / "zone.yaml"
        zone_path.write_text(yaml.dump(current_zone, default_flow_style=False))
    click.echo(f"Zone '{zone_id}' generated and connected to {location}.")


@engine.command()
def puzzle():
    """Show current zone's puzzle(s)."""
    gs = _load_state()
    location = gs.player["location"]
    zone = gs.get_zone(location)
    if not zone or not zone.get("puzzles"):
        click.echo("No puzzles in this zone.")
        return
    for puzzle_id in zone["puzzles"]:
        p = gs.get_puzzle(location, puzzle_id)
        if p:
            solved_str = " [SOLVED]" if p.get("solved") else ""
            click.echo(f"=== {p['name']}{solved_str} ===")
            click.echo(f"ID: {puzzle_id}")
            click.echo(f"Difficulty: {p.get('difficulty', '?')}")
            click.echo(f"Type: {p.get('type', 'unknown')}")
            click.echo(f"\n{p.get('narrative', '')}")
            mode = gs.meta.get("mode", "story")
            if mode == "technical":
                stub_path = gs.game_dir / "world" / location / puzzle_id / "solution_stub.py"
                if stub_path.exists():
                    click.echo(f"\nSolution stub: {stub_path}")
                    click.echo(stub_path.read_text())


@engine.command()
@click.argument("puzzle_id")
@click.option("--solution", required=True, type=str, help="Path to solution.py")
def solve(puzzle_id: str, solution: str):
    """Submit a puzzle solution."""
    gs = _load_state()
    location = gs.player["location"]
    puzzle_data = gs.get_puzzle(location, puzzle_id)
    if not puzzle_data:
        click.echo(f"Puzzle '{puzzle_id}' not found in {location}.")
        return
    if puzzle_data.get("solved"):
        click.echo(f"Puzzle '{puzzle_data['name']}' is already solved!")
        return
    solution_path = Path(solution)
    if not solution_path.exists():
        click.echo(f"Error: solution file not found: {solution}", err=True)
        return
    validate_path = gs.game_dir / "world" / location / puzzle_id / "validate.py"
    if not validate_path.exists():
        click.echo(f"Error: validator not found at {validate_path}", err=True)
        return
    validator = PuzzleValidator()
    result = validator.run(validate_path, solution_path)
    if result.passed:
        gs.mark_puzzle_solved(location, puzzle_id)
        profile = PlayerProfile(gs.game_dir / "player")
        profile.record_puzzle_attempt(puzzle_id, solved=True, puzzle_type=puzzle_data.get("type"))
        profile.save()
        solved_list = gs.player.setdefault("puzzles_solved", [])
        if puzzle_id not in solved_list:
            solved_list.append(puzzle_id)
            gs._save_player()
        click.echo(f"SOLVED: {puzzle_data['name']}")
    else:
        profile = PlayerProfile(gs.game_dir / "player")
        profile.record_puzzle_attempt(puzzle_id, solved=False)
        profile.save()
        click.echo(f"FAILED: {result.error}")


@engine.command()
@click.argument("puzzle_id")
def hint(puzzle_id: str):
    """Get a hint for a puzzle."""
    gs = _load_state()
    location = gs.player["location"]
    hints_used = gs.player.setdefault("hints_used", {})
    hint_index = hints_used.get(puzzle_id, 0)
    hint_text = gs.get_puzzle_hint(location, puzzle_id, hint_index)
    if hint_text:
        click.echo(f"Hint: {hint_text}")
        hints_used[puzzle_id] = hint_index + 1
        gs._save_player()
    else:
        click.echo("No more hints available.")


@engine.command()
def inventory():
    """Show player inventory."""
    gs = _load_state()
    items = gs.player.get("inventory", [])
    if not items:
        click.echo("Inventory is empty. No items yet.")
    else:
        click.echo("Inventory:")
        for item in items:
            click.echo(f"  - {item}")


@engine.command("add-item")
@click.argument("item_name")
@click.option("--description", default="", help="Item description.")
def add_item(item_name: str, description: str):
    """Add an item to the player's inventory."""
    gs = _load_state()
    gs.add_to_inventory(item_name)
    click.echo(f"Added '{item_name}' to inventory.")


@engine.command()
@click.argument("npc_id")
def talk(npc_id: str):
    """Talk to an NPC in the current zone."""
    gs = _load_state()
    location = gs.player["location"]
    npc_path = gs.game_dir / "world" / location / npc_id / "npc.yaml"
    if not npc_path.exists():
        click.echo(f"NPC '{npc_id}' not found in {location}.")
        return
    npc = yaml.safe_load(npc_path.read_text())
    click.echo(f"=== {npc.get('name', npc_id)} ===")
    click.echo(f"{npc.get('description', '')}\n")
    dialogue = npc.get("dialogue", {})
    for key, line in dialogue.items():
        click.echo(f"  [{key}]: \"{line}\"")


@engine.command()
def companions():
    """List companions in the party."""
    gs = _load_state()
    comp_list = gs.player.get("companions", [])
    companions_dir = gs.game_dir / "player" / "companions"
    if not comp_list:
        click.echo("You are traveling alone.")
        return
    click.echo("Your companions:\n")
    for comp_id in comp_list:
        comp_file = companions_dir / f"{comp_id}.yaml"
        if comp_file.exists():
            comp = yaml.safe_load(comp_file.read_text())
            click.echo(f"  {comp.get('name', comp_id)} — {comp.get('title', '')}")
            click.echo(f"    {comp.get('description', '')}")
            for ability in comp.get("abilities", []):
                click.echo(f"    • {ability['name']}: {ability['description']}")
            click.echo()
        else:
            click.echo(f"  {comp_id}")


@engine.command("map")
def show_map():
    """Show a map of explored zones."""
    gs = _load_state()
    visited = gs.player.get("zones_visited", [])
    location = gs.player["location"]
    click.echo("=== World Map ===\n")
    for zone_id in visited:
        marker = " <-- YOU ARE HERE" if zone_id == location else ""
        zone = gs.get_zone(zone_id)
        name = zone["name"] if zone else zone_id
        click.echo(f"  [{name}]{marker}")
        if zone and zone.get("connections"):
            for conn_id, conn in zone["connections"].items():
                if conn_id not in visited:
                    click.echo(f"    → {conn.get('name', conn_id)} [{conn.get('status', '?')}]")


@engine.command()
def profile():
    """Show player profile and adaptation data."""
    gs = _load_state()
    prof = PlayerProfile(gs.game_dir / "player")
    click.echo("=== Player Profile ===\n")
    signals = prof.data.get("skill_signals", {})
    click.echo(f"Avg attempts per puzzle: {signals.get('avg_attempts_per_puzzle', 0):.1f}")
    click.echo(f"Technical comfort: {signals.get('technical_comfort', 0):.1f}")
    click.echo(f"Preferred interaction: {signals.get('preferred_interaction', 'balanced')}")
    click.echo(f"Puzzle types enjoyed: {', '.join(signals.get('puzzle_types_enjoyed', [])) or 'none yet'}")
    hints = prof.data.get("generation_hints", {})
    click.echo(f"\nDifficulty target: {hints.get('difficulty_target', 1.0):.1f}")
    click.echo(f"More of: {', '.join(hints.get('more_of', [])) or 'no preferences yet'}")
    click.echo(f"Less of: {', '.join(hints.get('less_of', [])) or 'no preferences yet'}")


@engine.command()
@click.argument("direction")
def scout(direction: str):
    """Scout an adjacent zone (Scout companion ability)."""
    gs = _load_state()
    if "scout" not in gs.player.get("companions", []):
        click.echo("You don't have a Scout companion yet.")
        return
    location = gs.player["location"]
    zone = gs.get_zone(location)
    if not zone:
        click.echo("Cannot scout from unknown location.")
        return
    connections = zone.get("connections", {})
    if direction in connections:
        conn = connections[direction]
        click.echo(f"Scout report for {conn.get('name', direction)}:")
        click.echo(f"  {conn.get('teaser', 'No details available.')}")
        target_zone = gs.get_zone(direction)
        if target_zone:
            click.echo("  Status: Explored")
            if target_zone.get("puzzles"):
                click.echo(f"  Contains puzzles: {', '.join(target_zone['puzzles'])}")
        else:
            click.echo("  Status: Unexplored — will be generated on entry")
    else:
        click.echo(f"No known path in direction '{direction}'.")


@engine.command()
@click.argument("topic")
def research(topic: str):
    """Scholar researches a topic (Scholar companion ability)."""
    gs = _load_state()
    if "scholar" not in gs.player.get("companions", []):
        click.echo("You don't have a Scholar companion yet.")
        return
    location = gs.player["location"]
    zone = gs.get_zone(location)
    click.echo(f"Scholar researches '{topic}'...\n")
    if zone and zone.get("puzzles"):
        for puzzle_id in zone["puzzles"]:
            if topic.lower() in puzzle_id.lower() or puzzle_id.lower() in topic.lower():
                p = gs.get_puzzle(location, puzzle_id)
                if p:
                    click.echo(f"Research findings on '{p['name']}':")
                    for h in p.get("hints", []):
                        click.echo(f"  • {h}")
                    return
    click.echo(f"The Scholar ponders '{topic}' but finds no specific information in this zone.")


@engine.command()
@click.argument("description")
def craft(description: str):
    """Tinker crafts something (Tinker companion ability)."""
    gs = _load_state()
    if "tinker" not in gs.player.get("companions", []):
        click.echo("You don't have a Tinker companion yet.")
        return
    click.echo(f"The Tinker considers how to craft: '{description}'")
    click.echo("(Craft output should be interpreted by Claude to generate a solution file)")


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
    from agentic_quest.consequences import ConsequenceManager
    gs = _load_state()
    cm = ConsequenceManager(gs.game_dir)
    cm.schedule(description, trigger_after_moves=after, zone=zone, event_type=event_type)
    click.echo(f"Scheduled: '{description}' (in {after} moves)")


@engine.command()
def consequences():
    """Show pending scheduled events."""
    gs = _load_state()
    from agentic_quest.consequences import ConsequenceManager
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
    from agentic_quest.achievements import AchievementEngine
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
    from agentic_quest.achievements import AchievementEngine
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


@engine.command()
@click.argument("text")
@click.option("--voice", default="Samantha", help="macOS voice name.")
@click.option("--rate", default=180, help="Speech rate (words per minute).")
def say(text: str, voice: str, rate: int):
    """Read text aloud using macOS text-to-speech (runs in background)."""
    import platform
    import subprocess
    if platform.system() != "Darwin":
        click.echo("Voice synthesis is only available on macOS.")
        return
    subprocess.Popen(
        ["say", "-v", voice, "-r", str(rate), text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    click.echo("Speaking...")


@engine.command()
def pregenerate():
    """Pre-generate all stub zones adjacent to current location."""
    gs = _load_state()
    meta = gs.meta
    eco = _is_eco_mode()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not eco and not api_key:
        click.echo("Error: ANTHROPIC_API_KEY not set. Set it or enable eco mode (ECO=on).", err=True)
        raise SystemExit(1)

    from agentic_quest.generator import ZoneGenerator

    location = gs.player["location"]
    zone = gs.get_zone(location)
    if not zone or not zone.get("connections"):
        click.echo("No adjacent zones to pre-generate.")
        return

    preset_dir = _find_presets_dir() / meta.get("preset", "fantasy")
    gen = ZoneGenerator(game_dir=gs.game_dir, preset_dir=preset_dir, api_key=api_key, eco=eco)
    profile = PlayerProfile(gs.game_dir / "player")

    generated = 0
    for conn_id, conn in zone["connections"].items():
        if gs.get_zone(conn_id) is not None:
            continue  # already generated
        context = {
            "adjacent_zones": [location],
            "player_profile": profile.data,
            "difficulty": profile.data["generation_hints"]["difficulty_target"],
            "pacing": "exploration",
            "world_seed": meta.get("seed", 42),
            "inventory": gs.player.get("inventory", []),
            "open_puzzles": [],
        }
        click.echo(f"Pre-generating '{conn.get('name', conn_id)}'...")
        gen.generate_full_zone(conn_id, context)
        conn["status"] = "generated"
        generated += 1

    if generated > 0:
        # Update connection statuses
        zone_path = gs.game_dir / "world" / location / "zone.yaml"
        zone_path.write_text(yaml.dump(zone, default_flow_style=False))

    click.echo(f"Pre-generated {generated} zone(s).")
