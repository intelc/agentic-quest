# Post-Playtest Improvements Spec

**Date:** 2026-04-06
**Status:** Approved
**Based on:** 3 playtests (sessions 1a0f2c5b, 55671038, aeb7921d) + competitive analysis of 5 reference projects

---

## Improvement 1: Persist-Before-Narrate Rule

**Source:** Claude Code Game Master pattern
**Problem:** If Claude's session drops mid-narration, state changes that were only narrated but not yet persisted are lost.
**Fix:** Add explicit rule to CLAUDE.md: always run engine mutation commands BEFORE narrating their result to the player. Add a state-change table mapping every world event to its required engine command.
**Effort:** Low (~10 min, CLAUDE.md only)

---

## Improvement 2: NPC Event History / Memory

**Source:** Claude Code Game Master (NPC events array) + Intra (perspective-filtered history)
**Problem:** NPCs have no memory across turns. The merchant doesn't remember you solved the signpost. Lyra doesn't remember scouting the forest. This makes the world feel lifeless.
**Fix:**
- Add `events` array to NPC yaml files
- New engine command: `engine record-event <npc_id> "<event description>"`
- Engine appends `{event, timestamp, zone}` to the NPC's events list
- `engine talk <npc_id>` includes the NPC's recent events (last 10) in output
- CLAUDE.md instructs narrator to call `record-event` after significant NPC interactions
**Effort:** Medium (~1 hour — state.py, cli.py, CLAUDE.md)

---

## Improvement 3: Consequence / Scheduled Events System

**Source:** Claude Code Game Master (consequence_manager.py) + SkillsWeaver (foreshadowing system)
**Problem:** The world is purely reactive — things only happen when the player looks at them. Nothing evolves on its own. No sense of time passing or events unfolding.
**Fix:**
- New file: `world/consequences.json` — list of scheduled events
- Each consequence: `{id, description, trigger_after_moves: N, zone: "optional", type: "npc_appears|path_opens|item_appears|narrative_event"}`
- Engine ticks consequences on every `engine move` — if `trigger_after_moves` reached 0, fire it
- New command: `engine schedule "<description>" --after <N> [--zone <zone_id>] [--type <type>]`
- New command: `engine consequences` — list pending consequences
- CLAUDE.md instructs narrator to schedule consequences after significant events ("merchant will send a message in 3 moves")
**Effort:** Medium (~2 hours — new consequence module, cli commands, CLAUDE.md)

---

## Improvement 4: Structured Output Templates

**Source:** Claude Code Game Master (output-format.md slot)
**Problem:** Claude's narration format varies wildly — sometimes long prose, sometimes bullets, sometimes code leaks. No consistent "game feel."
**Fix:** Add output template section to CLAUDE.md defining consistent formats for:
- **Scene header:** zone name, atmosphere line
- **Narrative block:** 2-3 paragraphs of second-person description
- **NPC dialogue:** name in bold, quoted speech, italicized action
- **Puzzle prompt:** framed challenge with clear stakes
- **Choice menu:** lettered options with em-dash descriptions
- **Voice narration:** what to pass to `engine say` (concise, sensory)
- **Solve celebration:** dramatic moment + world reaction
**Effort:** Low (~30 min, CLAUDE.md only)

---

## Improvement 5: Session Context Command

**Source:** Claude Code Game Master (dm-session.sh context)
**Problem:** On every session start and resume, Claude runs 4-5 sequential engine commands (status, look, paths, companions, puzzle). Each adds latency. Total: ~15 seconds of tool calls before the first narration.
**Fix:**
- New command: `engine context` — returns a single aggregated output with:
  - Player state (location, inventory, companions)
  - Current zone narrative
  - Available paths with status
  - Active puzzles (unsolved)
  - NPCs in current zone
  - Recent events (last 5)
  - Pending consequences
  - Player profile summary
- Optional `--full` flag for verbose output
- CLAUDE.md game loop step 1 becomes just `engine context`
**Effort:** Medium (~1 hour — cli.py)

---

## Improvement 6: Perspective-Filtered NPC Knowledge

**Source:** Intra (updatesSeenByMe() method)
**Problem:** Claude can accidentally have NPCs reference things they shouldn't know. An NPC in the forest shouldn't know you solved the crossroads puzzle unless they were there.
**Fix:**
- Track which zone each event occurred in (already part of Improvement 2's event format)
- `engine talk <npc_id>` filters events to only include those where the NPC was in the same zone
- NPCs that have traveled with the player (companions) see all events
- Static NPCs (merchants, quest givers) only see events in their zone
**Effort:** Medium (~2 hours — requires Improvement 2 first, then filtering logic in state.py/cli.py)

---

## Improvement 7: Freeform Interaction Triggers

**Source:** Playtest 2 & 3 feedback — the "Sun Star Moon" moment was the most engaging turn
**Problem:** Players default to picking A/B/C/D from menus. The game's unique value — natural language problem-solving — only surfaces during puzzles. Need more moments that REQUIRE creative input.
**Fix:**
- Add `interaction_type` field to puzzle.yaml: `"describe"` (explain your logic), `"choose"` (pick from options), `"create"` (invent something new), `"name"` (name something)
- Generation prompts create a mix of interaction types
- CLAUDE.md rule: at least every 3rd turn must require freeform input, not just menu selection
- Non-puzzle freeform prompts:
  - "What do you say to the merchant?" (dialogue)
  - "Name your newly found weapon." (naming)
  - "Describe what you see when you look through the crystal." (imagination)
  - "The path splits. There are no signs. Where does your gut tell you to go?" (intuition)
  - "The inscription is faded. What do you think it once said?" (creation)
- CLAUDE.md tracks a `turns_since_freeform` counter and forces freeform when it hits 3
**Effort:** Medium (~1 hour — puzzle.yaml schema, generation prompts, CLAUDE.md)

---

## Improvement 8: Achievement / Milestone System

**Source:** Claude Quest (declarative achievement schema with detection types)
**Problem:** No sense of progression beyond "puzzles solved" count. No celebration of exploration milestones, NPC interactions, or creative play.
**Fix:**
- New file: `player/achievements.json` — tracks unlocked achievements
- Achievement definitions in preset: `presets/fantasy/achievements.json`
- Each achievement: `{id, name, description, category, xp, rarity, trigger: {type, ...}}`
- Trigger types: `puzzle_solved`, `zones_visited` (count), `npcs_talked` (count), `items_found`, `companions_unlocked`, `freeform_answers` (count), `custom`
- Categories: exploration, puzzle-solving, social, discovery, creativity
- New command: `engine achievements` — shows unlocked + next recommended
- New command: `engine check-achievements` — evaluates all triggers against current state, unlocks new ones
- Engine auto-checks achievements after puzzle solves and zone transitions
- "Next quest" recommendations: always suggest 2-3 achievable goals
- Rarity-based XP: common=10, uncommon=25, rare=50, epic=100, legendary=250
**Effort:** High (~3 hours — new module, achievement definitions, cli commands, CLAUDE.md)

---

## Implementation Order

```
Improvement 1 (persist-before-narrate)     — no dependencies
Improvement 4 (output templates)           — no dependencies
Improvement 5 (engine context)             — no dependencies
Improvement 2 (NPC memory)                 — no dependencies
Improvement 3 (consequences)               — no dependencies
Improvement 7 (freeform triggers)          — no dependencies
Improvement 6 (NPC perspective filtering)  — depends on Improvement 2
Improvement 8 (achievements)               — benefits from 2, 3, 7
```

Improvements 1, 4, 5 can be done in parallel (different files).
Improvements 2, 3 can be done in parallel (different modules).
Improvement 6 depends on 2.
Improvement 8 should be last (benefits from all others).
