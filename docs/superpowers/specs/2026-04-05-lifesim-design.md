# LifeSim — Design Spec

**Date:** 2026-04-05
**Status:** Draft
**Approach:** Thin Engine (Approach B)

## Vision

An LLM-powered text RPG delivered as a folder opened in Claude Code. Users explore a procedurally generated world, solve narrative-framed puzzles backed by real code validators, and employ subagents as in-game companions. The core thesis: give non-technical users the thrill of vibecoding — agency, problem-solving, orchestrating AI agents — without requiring them to know they're programming.

## Architecture

Three layers, strict separation of concerns:

### 1. Narrative Layer (Claude + CLAUDE.md)
- Claude is the game master / narrator
- CLAUDE.md is generated at init, templated to the chosen preset and mode
- Claude interprets player intent, voices companions, narrates outcomes
- Claude **never modifies game files directly** — always calls engine CLI

### 2. Engine Layer (Python CLI)
- State management (player position, inventory, companions, profile)
- Terrain generator (creates zones/puzzles on demand via LLM calls)
- Validator runner (executes puzzle validators, returns pass/fail + feedback)
- Player profile tracker (observes behavior, feeds into generation)
- Exposes everything via CLI commands that Claude calls through Bash

### 3. World Layer (Files)
- `world/` — generated terrain as folders/files
- `player/` — player state, inventory, companions, profile
- `presets/` — genre templates with generation prompts

**Key constraint:** Claude never modifies game state directly. Claude calls engine commands → engine modifies files → Claude reads results and narrates. This keeps state consistent and validators enforceable.

## World Structure

Each zone is a folder:

```
world/
├── _meta.yaml                  # world seed, theme, generation rules
├── crossroads/                 # starting zone
│   ├── zone.yaml               # description, connections, NPCs
│   ├── narrative.md            # what Claude reads to the player
│   ├── old_merchant/           # NPC
│   │   └── npc.yaml            # dialogue, inventory, quests
│   └── broken_signpost/        # puzzle
│       ├── puzzle.yaml         # narrative framing, hints, difficulty
│       ├── validate.py         # validator function
│       └── solution_stub.py    # function stub (technical mode)
├── dark_forest/                # generated on demand
│   └── ...
└── __unexplored__/             # placeholder for ungenerated zones
    └── connections.yaml        # which explored zones connect here
```

### Terrain Generation Strategy — Hybrid Chunking

1. Player enters a zone → engine generates **stubs** for all connected zones (name, 1-line teaser, connection type)
2. Player chooses a direction → engine **fully generates** that zone (narrative, NPCs, puzzles, items)
3. Player does something unexpected → engine generates a **new zone on the fly**, connects it to current location
4. Generation uses the **world seed + preset theme + player profile + local context** for coherence

The generator is itself an LLM call — it writes yaml/py files based on the preset's generation prompt templates. The engine invokes the Anthropic API (Claude) directly for generation, using the preset's prompt templates with world context injected. This is a programmatic API call from the engine, separate from the Claude Code session that the player interacts with.

## Interaction Model — Hybrid

- Choices are presented for discovery and guidance (e.g., "You see three paths...")
- Freeform natural language input is always accepted
- Unexpected actions trigger on-demand zone generation
- Choices are guardrails, not walls

## Puzzle System

### Puzzle Types (MVP: function completion only)

**Function Completion (MVP flagship):**
A stub function with a docstring/narrative description. The solution is completing it. Non-technical users describe the logic in natural language, Claude translates to code, engine runs validator. Technical users write code directly.

**State Mutation (v2):**
A `state.json` needs to reach a target configuration through multi-step actions.

**Output Generation (v2):**
User must produce an artifact that the validator checks for specific properties.

**Discovery / Exploration (v2):**
No code validator — engine checks if player visited the right places or talked to the right NPCs.

### Dual-Mode Experience

**Non-technical (story mode):**
1. Claude narrates the puzzle as a world event
2. User describes their logic in plain language: "Try the sun first, then the moon, then the star"
3. Claude translates intent into code (invisible to user)
4. Engine runs validator
5. Claude narrates success/failure as a world event — never mentions code, test cases, or validators

**Technical mode:**
1. Claude gives shorter narrative + shows the solution stub and validator signature
2. User writes code directly or describes logic for Claude to translate
3. Engine runs validator, shows results
4. Claude narrates alongside engine output

### Non-Technical → Code Translation Flow

```
User intent → Claude translates → engine solve (runs validator) → Claude narrates outcome
```

Non-technical users never see steps 2-3. Technical users can see and modify the generated code before submission.

## Companions — Fixed Archetypes, Emergent Personality

Four companion archetypes, each mapping to a real agent capability:

| Archetype | Agent Type | Role |
|-----------|-----------|------|
| Scout | Explore subagent | Scan ahead, find hidden paths, reveal map |
| Scholar | Research subagent | Deep lore, puzzle analysis, hint generation |
| Tinker | Code-writing subagent | Build solutions, repair mechanisms, craft items |
| Cartographer | State/map subagent | Render world map, recall past events, manage inventory |

**Fixed:** The archetype-to-agent mapping (Scout always = Explore agent).
**Emergent:** Name, appearance, personality, dialogue, backstory — all generated by the preset and adapted to the player.

Users interact naturally: "Scout, what's ahead?" or "Ask the Tinker to build a bridge." Claude responds in character AND dispatches the appropriate engine command.

## Progression — Emergent, Not Hardcoded

### Player Profile

The engine maintains `player/profile.yaml`, auto-updated as the player interacts:

```yaml
skill_signals:
  puzzle_types_enjoyed: ["function_completion"]
  avg_attempts_per_puzzle: 2.3
  preferred_interaction: "exploration_heavy"
  technical_comfort: 0.3          # 0 = pure narrative, 1 = raw code
  language_patterns:
    - "tends to think in sequences/steps"
    - "uses spatial metaphors"
  interests_detected:
    - "astronomy"
    - "mechanical puzzles"
generation_hints:
  more_of: ["exploration", "mechanical puzzles"]
  less_of: ["timed challenges"]
  difficulty_target: 2.5
```

### Emergent Tools & Gating (v2)

Tools and items are generated based on player behavior, not from a fixed table. The engine observes patterns and generates contextually appropriate items:

- Player keeps scanning ahead → Watchtower appears (auto-reveals adjacent zones)
- Player stuck on a puzzle → Wandering NPC arrives with a Hint Lantern
- Player's technical curiosity rising → Eye of Truth manifests (peek at code in story mode)

### Adaptive Difficulty (v2)

Generation rules, not a fixed world graph:
- New zones target `player.difficulty_target ± 0.5`
- Tool gating: locks may require tools the player has (mastery) or doesn't have (placed nearby)
- Breadcrumbing: new zones may contain hints for old unsolved puzzles
- Pacing: alternate puzzle-heavy and exploration/story zones

## Preset System

A preset is a folder defining a genre's generation templates, starter world, and narrative voice:

```
presets/fantasy/
├── preset.yaml            # metadata
├── voice.md               # narrative style guide for Claude
├── generation/
│   ├── zone.prompt        # LLM prompt template to generate a zone
│   ├── puzzle.prompt       # LLM prompt template to generate a puzzle
│   ├── npc.prompt          # LLM prompt template to generate an NPC
│   └── item.prompt         # LLM prompt template to generate a tool/item
├── starter/               # pre-built starting zone
│   └── crossroads/
└── companions/
    ├── scout.yaml         # Scout's fantasy persona
    ├── scholar.yaml
    ├── tinker.yaml
    └── cartographer.yaml
```

Generation prompts are templates that receive: adjacent zones, player profile, difficulty target, pacing hint, world seed, player inventory, and unsolved puzzles as context.

MVP ships with 1 preset (fantasy). Additional presets (sci-fi, post-apocalyptic) in v2.

## Engine CLI

```
# Game lifecycle
engine init --preset fantasy --mode story
engine status
engine save [name]                    # v2
engine restore <name>                 # v2

# Movement & exploration
engine look
engine paths
engine move <zone_id>
engine generate <direction|description>

# Puzzles
engine puzzle
engine solve <puzzle_id> --solution <file>
engine hint <puzzle_id>

# Companions & subagent dispatch
engine companions
engine scout <zone_id|direction>
engine research <topic>
engine craft <description>
engine map

# Player profile
engine inventory
engine profile
engine profile update
```

## CLAUDE.md — Generated at Init

Templated to preset + mode. Instructs Claude on:
- Narrative voice (from preset's voice.md)
- Player mode (story vs technical) and corresponding behavior
- How to use engine CLI commands
- How to voice companions
- The core game loop: `engine status` → `engine look` → present choices → respond to input → update narrative

## User Onboarding

```bash
pip install lifesim
lifesim new my-adventure --preset fantasy --mode story
# Open my-adventure/ in Claude Code
# Claude reads CLAUDE.md, runs engine status, greets player in-character
# Play.
```

## Persistence

**MVP:** File-system is the live state. Session resume works by Claude reading CLAUDE.md → running `engine status` → narrating a recap of where the player left off.

**v2:** Save/restore system with named snapshots. Auto-save on puzzle solve and zone transition. World zones persist across restores (only player state reverts). Eventually git-backed.

## MVP Scope

### v1 (MVP)
- Engine CLI (Python): init, status, look, paths, move, puzzle, solve, hint, companions, inventory, scout, research, craft, map, profile
- 1 preset (fantasy)
- Terrain generation via LLM (zone + puzzle generation prompts)
- Player profile tracking (basic — puzzle attempts, difficulty adjustment)
- Dual mode (story / technical) set at init
- 4 companion archetypes with subagent dispatch
- Function completion puzzle type
- CLAUDE.md generation at init
- File-system as live state

### v2
- Additional presets (sci-fi, post-apocalyptic)
- Save/restore system (eventually git-backed)
- State mutation + output generation puzzle types
- Emergent tool generation from player profile
- Adaptive pacing rules
- Eye of Truth mode bridge
- Discovery/exploration puzzle type

### v3+
- Custom harness (beyond Claude Code)
- Multiplayer / shared worlds
- Community preset marketplace
- Custom preset builder

## Open Questions

None — all key decisions have been made through the brainstorming process.
