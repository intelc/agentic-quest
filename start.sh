#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Defaults
ADVENTURE_DIR=""
SOURCE=""
MODE="story"
PRESET="fantasy"

# Parse args: ./start.sh [adventure-dir] [--source file] [--mode story|technical] [--preset name]
while [[ $# -gt 0 ]]; do
    case $1 in
        --source|-s)
            SOURCE="$2"
            shift 2
            ;;
        --mode|-m)
            MODE="$2"
            shift 2
            ;;
        --preset|-p)
            PRESET="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./start.sh [adventure-dir] [--source file] [--mode story|technical] [--preset name]"
            echo ""
            echo "Examples:"
            echo "  ./start.sh                              # new fantasy adventure at ./my-adventure"
            echo "  ./start.sh my-game                      # new fantasy adventure at ./my-game"
            echo "  ./start.sh my-game --source wuxia.txt   # world from fiction (Chinese, English, any language)"
            echo "  ./start.sh my-game --mode technical      # see the code behind puzzles"
            exit 0
            ;;
        *)
            ADVENTURE_DIR="$1"
            shift
            ;;
    esac
done

ADVENTURE_DIR="${ADVENTURE_DIR:-$SCRIPT_DIR/my-adventure}"

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       A G E N T I C  Q U E S T       ║"
echo "  ║  Drop into any fiction. Play inside.  ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check for Python
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required. Install Python 3.11+ first."
    exit 1
fi

# Detect agent CLI (Claude Code or Codex)
AGENT_CLI=""
if [ -n "$AQ_AGENT" ]; then
    AGENT_CLI="$AQ_AGENT"
elif command -v claude &>/dev/null; then
    AGENT_CLI="claude"
elif command -v codex &>/dev/null; then
    AGENT_CLI="codex"
else
    echo "Error: No agent CLI found."
    echo "Install Claude Code: https://claude.ai/download"
    echo "  or Codex: npm install -g @openai/codex"
    exit 1
fi
echo -e "${GREEN}Using agent: ${AGENT_CLI}${NC}"

# Install aq if not already installed
if ! command -v aq &>/dev/null; then
    echo -e "${YELLOW}Installing aq...${NC}"
    pip install -e "$SCRIPT_DIR" --quiet
    echo -e "${GREEN}Installed.${NC}"
fi

# Check for eco mode (uses Claude Code CLI for generation — no API key needed)
_ECO=""
for envfile in "$ADVENTURE_DIR/.env" "$SCRIPT_DIR/.env" "$HOME/.env"; do
    if [ -f "$envfile" ]; then
        _ECO=$(grep -v '^#' "$envfile" | grep '^ECO=' | head -1 | cut -d= -f2- | tr -d "'" | tr -d '"' | tr -d ' ')
        if [ -n "$_ECO" ]; then break; fi
    fi
done
if [ -n "$ECO" ]; then
    _ECO="$ECO"
fi

if [[ "$_ECO" =~ ^(on|true|1)$ ]]; then
    echo -e "${GREEN}Eco mode enabled — using Claude Code for generation (no API key needed).${NC}"
    _API_KEY=""
else
    _API_KEY=""
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        _API_KEY="$ANTHROPIC_API_KEY"
        unset ANTHROPIC_API_KEY
    else
        for envfile in "$ADVENTURE_DIR/.env" "$SCRIPT_DIR/.env" "$HOME/.env"; do
            if [ -f "$envfile" ]; then
                _API_KEY=$(grep -v '^#' "$envfile" | grep ANTHROPIC_API_KEY | head -1 | cut -d= -f2- | tr -d "'" | tr -d '"' | tr -d ' ')
                if [ -n "$_API_KEY" ]; then break; fi
            fi
        done
    fi

    if [ -z "$_API_KEY" ]; then
        echo -e "${YELLOW}Warning: ANTHROPIC_API_KEY not found.${NC}"
        echo "Zone generation won't work without it."
        echo "Create a .env file with: ANTHROPIC_API_KEY=your-key"
        echo "Or enable eco mode: ECO=on (uses Claude Code CLI instead)"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Create adventure if it doesn't exist
if [ ! -f "$ADVENTURE_DIR/CLAUDE.md" ]; then
    _SOURCE_FLAG=""
    if [ -n "$SOURCE" ]; then
        echo -e "${GREEN}Creating world from source: ${SOURCE}${NC}"
        _SOURCE_FLAG="--source $SOURCE"
    else
        echo -e "${GREEN}Creating new ${PRESET} adventure in ${MODE} mode...${NC}"
    fi
    aq new "$ADVENTURE_DIR" --preset "$PRESET" --mode "$MODE" $_SOURCE_FLAG

    # Write .env into adventure dir so the engine can find it
    if [ ! -f "$ADVENTURE_DIR/.env" ]; then
        _ENV_CONTENT="AQ_AGENT=$AGENT_CLI"
        if [ -n "$_API_KEY" ]; then
            _ENV_CONTENT="${_ENV_CONTENT}
ANTHROPIC_API_KEY=$_API_KEY"
        fi
        if [[ "$_ECO" =~ ^(on|true|1)$ ]]; then
            _ENV_CONTENT="${_ENV_CONTENT}
ECO=on"
        fi
        echo "$_ENV_CONTENT" > "$ADVENTURE_DIR/.env"
    fi

    echo ""
    echo -e "${GREEN}Adventure created!${NC}"
else
    echo -e "${GREEN}Resuming adventure at ${ADVENTURE_DIR}${NC}"
    if [ ! -f "$ADVENTURE_DIR/.env" ]; then
        _ENV_CONTENT=""
        if [ -n "$_API_KEY" ]; then
            _ENV_CONTENT="ANTHROPIC_API_KEY=$_API_KEY"
        fi
        if [[ "$_ECO" =~ ^(on|true|1)$ ]]; then
            _ENV_CONTENT="${_ENV_CONTENT:+$_ENV_CONTENT
}ECO=on"
        fi
        if [ -n "$_ENV_CONTENT" ]; then
            echo "$_ENV_CONTENT" > "$ADVENTURE_DIR/.env"
        fi
    fi
fi

echo ""
echo -e "${CYAN}Launching ${AGENT_CLI}...${NC}"
echo ""

# Launch the agent in the adventure directory with an opening message
cd "$ADVENTURE_DIR"
if [ "$AGENT_CLI" = "codex" ]; then
    exec codex "I just arrived. What do I see?"
else
    exec claude "I just arrived. What do I see?"
fi
