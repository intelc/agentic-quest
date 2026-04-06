<div align="center">

```
  ╔═══════════════════════════════════════╗
  ║       A G E N T I C  Q U E S T       ║
  ║  Drop into any fiction. Play inside.  ║
  ╚═══════════════════════════════════════╝
```

**Drop in any fiction. Play inside the story.**

An LLM-powered text RPG where your puzzles are real code, your companions are AI agents, and the world generates around you. Works with Claude Code and Codex.

[Quick Start](#quick-start) | [Features](#what-makes-this-different) | [How It Works](#how-it-works) | [Source Worlds](#play-inside-any-fiction)

</div>

---

## Quick Start

```bash
git clone https://github.com/user/agentic-quest.git
cd agentic-quest
./start.sh
```

Three commands. The script installs everything, creates a fantasy adventure, and launches Claude Code with the game already running. You'll see something like:

```
=== The Crossroads ===

You stand at a crossroads beneath an open sky. A weathered signpost leans
to one side. An old merchant sits nearby, arranging curious wares...

[A] Examine the broken signpost — the symbols might mean something
[B] Approach the old merchant — he seems eager to talk
[C] Ask Lyra to scout the Dark Forest path
[D] Something else (describe what you'd like to do)
```

Type a letter or describe what you want to do. The world responds.

---

## What Makes This Different

Every other AI RPG lets the LLM make up whether you succeed or fail. Agentic Quest doesn't.

**Puzzles are real programs.** Each puzzle is backed by a Python validator function. When you say "arrange the symbols: sun, moon, star" — the AI translates your logic into code, runs it against the validator, and it either passes or it doesn't. No hallucinated victories.

**Two ways to play.**
- **Story mode** — you never see code. Describe your reasoning in plain words. The AI handles the rest.
- **Technical mode** — see the validator, write the solution yourself. Same puzzles, different interface.

**Companions are real AI agents.** Your Scout dispatches an Explore subagent. Your Scholar runs a research query. Your Tinker writes code. They're not flavor text — they do actual work.

**The world adapts to you.** The engine tracks how you play — what puzzles you enjoy, how many attempts you need, whether you prefer exploration or combat. Future zones are generated to match.

**Drop in any fiction.** Pass a text file — a novel excerpt, a short story, a game setting doc in any language — and the entire world generates from it. Chinese wuxia, sci-fi, post-apocalyptic survival. The narration matches the source language.

---

## Play Inside Any Fiction

```bash
# Chinese web novel
./start.sh my-wuxia --source wuxia_chapter1.txt

# English sci-fi
./start.sh my-expanse --source expanse_excerpt.txt

# Any language, any genre
./start.sh my-world --source your_fiction.txt
```

The source text becomes the DNA of your world. Locations, characters, tone, and puzzles are all grounded in the fiction. Future RAG support will allow full novels.

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│  AI Coding Agent (narrator)                     │
│  Reads CLAUDE.md → voices NPCs → narrates world │
│  ↕ calls engine commands via shell              │
├─────────────────────────────────────────────────┤
│  Engine CLI (Python)                            │
│  State · Validators · Generation · Profiles     │
│  ↕ reads/writes game files                      │
├─────────────────────────────────────────────────┤
│  Game Directory (files)                         │
│  world/  →  zones, puzzles, NPCs as YAML/Python │
│  player/ →  inventory, companions, profile      │
└─────────────────────────────────────────────────┘
```

The game is a folder. Your AI coding agent reads `CLAUDE.md` and becomes the game master. It calls `engine` commands to manage state — move, solve puzzles, talk to NPCs, generate new zones. The engine enforces rules; the AI handles narrative.

```
my-adventure/
├── CLAUDE.md           # Game master instructions
├── .claude/            # Auto-approved engine permissions
├── world/
│   ├── crossroads/     # Each zone is a folder
│   │   ├── zone.yaml       # Connections, NPCs, puzzles
│   │   ├── narrative.md     # What the AI reads to you
│   │   └── broken_signpost/
│   │       ├── puzzle.yaml      # Narrative framing
│   │       ├── validate.py      # Real Python validator
│   │       └── solution_stub.py # Function to complete
│   └── (more zones generated as you explore)
└── player/
    ├── state.yaml      # Location, inventory, companions
    ├── profile.yaml    # How the game adapts to you
    └── companions/     # Scout, Scholar, Tinker, Cartographer
```

---

## Commands

The AI calls these automatically. In technical mode, you can run them yourself.

| Command | What it does |
|---------|-------------|
| `engine context` | Everything at once (session start) |
| `engine look` | Describe current zone |
| `engine paths` | Available directions |
| `engine move <zone>` | Go somewhere (auto-generates if needed) |
| `engine puzzle` | Current puzzle details |
| `engine solve <id> --solution <file>` | Submit a solution |
| `engine hint <id>` | Get a narrative hint |
| `engine talk <npc>` | Talk to an NPC |
| `engine add-item <item>` | Pick up an item |
| `engine scout <zone_id>` | Scout companion scans ahead |
| `engine research <topic>` | Scholar companion investigates |
| `engine craft <desc>` | Tinker companion builds |
| `engine map` | Show explored world |
| `engine schedule <desc> --after <N>` | Schedule a future event |
| `engine check-achievements` | Check for new achievements |
| `engine say <text>` | Read aloud (macOS) |

---

## Modes

```bash
# Story mode (default) — pure narrative, no code visible
./start.sh my-adventure --mode story

# Technical mode — see validators, write solutions
./start.sh my-adventure --mode technical
```

**Story mode** is the "vibecoding for everyone" experience. You describe your thinking — "the sun comes first because it's the source of light, then the moon reflects it, then the star is farthest away" — and the AI translates that into a function that the validator checks. You never see a line of code.

**Technical mode** shows you the `validate.py` and `solution_stub.py`. You write the function yourself, or describe the logic and let the AI write it. Same puzzles, transparent mechanics.

---

## Requirements

- **Python 3.11+**
- **[Claude Code](https://claude.ai/download)** or **[Codex](https://openai.com/codex)** (Codex support coming soon)
- **ANTHROPIC_API_KEY** for zone generation — set via `.env` file or environment variable. Or use eco mode (`ECO=on` in `.env`) to generate via CLI instead.

---

## What's Next

- [ ] Codex support (multi-agent harness)
- [ ] RAG pipeline for full novels (play inside entire books)
- [ ] Multiplayer shared worlds
- [ ] More presets (sci-fi, post-apocalyptic, historical)
- [ ] Community preset marketplace

---

<div align="center">

Built for agentic coding tools

</div>
