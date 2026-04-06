# src/agentic_quest/generator.py
"""Zone generator — creates world content via Anthropic API or agent CLI (eco mode)."""
import json
import os
import re
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


class ZoneGenerator:
    """Generates zones, puzzles, and NPCs using LLM + preset prompt templates."""

    def __init__(self, game_dir: Path, preset_dir: Path, api_key: str | None = None, eco: bool = False):
        self.game_dir = Path(game_dir)
        self.preset_dir = Path(preset_dir)
        self._eco = eco
        if not eco:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
        self._jinja = Environment(
            loader=FileSystemLoader(str(self.preset_dir / "generation")),
            keep_trailing_newline=True,
        )

    def _render_prompt(self, template_name: str, context: dict) -> str:
        template = self._jinja.get_template(template_name)
        return template.render(**context)

    def _call_llm(self, prompt: str) -> str:
        if self._eco:
            return self._call_llm_eco(prompt)
        response = self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _detect_agent_cli(self) -> str:
        """Detect which agent CLI is available: 'claude' or 'codex'."""
        agent = os.environ.get("AQ_AGENT", "").lower()
        if agent in ("claude", "codex"):
            return agent
        # Auto-detect
        import shutil as _shutil
        if _shutil.which("claude"):
            return "claude"
        if _shutil.which("codex"):
            return "codex"
        raise RuntimeError("No agent CLI found. Install Claude Code or Codex.")

    def _call_llm_eco(self, prompt: str) -> str:
        """Call agent CLI (Claude Code or Codex) as a subprocess."""
        agent = self._detect_agent_cli()

        if agent == "claude":
            cmd = ["claude", "-p", prompt, "--output-format", "json"]
        else:
            cmd = ["codex", "exec", prompt]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{agent} CLI failed: {result.stderr}")
        raw = result.stdout.strip()

        # Extract result from CLI JSON envelope (Claude wraps in {"result": "..."})
        try:
            cli_output = json.loads(raw)
            if isinstance(cli_output, dict) and "result" in cli_output:
                raw = cli_output["result"]
        except (json.JSONDecodeError, TypeError):
            pass

        # Strip markdown code fences
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)
        # Extract JSON object/array from surrounding text
        raw = raw.strip()
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', raw)
        if json_match:
            raw = json_match.group(1)
        return raw.strip()

    @staticmethod
    def _repair_json(raw: str) -> str:
        """Attempt to repair common LLM JSON issues."""
        # Step 1: Fix unescaped newlines/tabs inside string values
        result = []
        in_string = False
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == '\\' and in_string:
                result.append(ch)
                if i + 1 < len(raw):
                    i += 1
                    result.append(raw[i])
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
            if in_string and ch == '\n':
                result.append('\\n')
            elif in_string and ch == '\t':
                result.append('\\t')
            else:
                result.append(ch)
            i += 1
        repaired = ''.join(result)

        # Step 2: Remove trailing commas before } or ]
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

        # Step 3: Try to fix truncated JSON by closing open brackets
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')
        if open_braces > 0 or open_brackets > 0:
            # Truncated — try to close it
            # First, if we're inside a string, close it
            if repaired.count('"') % 2 == 1:
                repaired += '"'
            repaired += ']' * max(0, open_brackets)
            repaired += '}' * max(0, open_braces)

        return repaired

    def _parse_json(self, raw: str) -> dict:
        """Try to parse JSON with multiple repair strategies."""
        # Strategy 1: Direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Repair and parse
        repaired = self._repair_json(raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Extract the largest valid JSON substring
        # Find all potential JSON objects and try to parse each
        for match in re.finditer(r'\{', raw):
            start = match.start()
            depth = 0
            for j in range(start, len(raw)):
                if raw[j] == '{':
                    depth += 1
                elif raw[j] == '}':
                    depth -= 1
                if depth == 0:
                    candidate = raw[start:j + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        repaired_candidate = self._repair_json(candidate)
                        try:
                            return json.loads(repaired_candidate)
                        except json.JSONDecodeError:
                            pass
                    break

        raise json.JSONDecodeError("All JSON repair strategies failed", raw, 0)

    def _parse_json_with_retry(self, prompt: str, max_retries: int = 2) -> dict:
        """Call LLM and parse JSON, retrying with a fix-your-JSON prompt on failure."""
        last_raw = ""
        for attempt in range(max_retries + 1):
            if attempt == 0:
                raw = self._call_llm(prompt)
            else:
                # Ask the LLM to fix its own broken JSON
                fix_prompt = (
                    "Your previous response was not valid JSON. Here is what you produced:\n\n"
                    f"{last_raw[:2000]}\n\n"
                    "Please output ONLY the corrected valid JSON. No explanation, no markdown fencing. "
                    "Make sure all strings are properly escaped and all brackets are closed."
                )
                raw = self._call_llm(fix_prompt)

            last_raw = raw
            try:
                return self._parse_json(raw)
            except json.JSONDecodeError:
                if attempt >= max_retries:
                    raise

    def _inject_source_material(self, context: dict):
        """Load source material from game dir and inject into context if available."""
        source_path = self.game_dir / "world" / "source.md"
        if source_path.exists() and "source_material" not in context:
            context["source_material"] = source_path.read_text()

    def generate_zone_stub(self, zone_id: str, context: dict) -> dict:
        self._inject_source_material(context)
        prompt = self._render_prompt("zone.prompt.j2", context)
        prompt += "\n\nGenerate ONLY a stub with: name, teaser, connections. Keep it brief."
        return self._parse_json_with_retry(prompt)

    def generate_full_zone(self, zone_id: str, context: dict):
        self._inject_source_material(context)
        prompt = self._render_prompt("zone.prompt.j2", context)
        data = self._parse_json_with_retry(prompt)

        zone_dir = self.game_dir / "world" / zone_id
        zone_dir.mkdir(parents=True, exist_ok=True)

        # Write zone.yaml
        (zone_dir / "zone.yaml").write_text(
            yaml.dump(data["zone"], default_flow_style=False, allow_unicode=True)
        )

        # Write narrative.md
        (zone_dir / "narrative.md").write_text(data["narrative"])

        # Write puzzles
        for puzzle_data in data.get("puzzles", []):
            puzzle_id = puzzle_data["id"]
            puzzle_dir = zone_dir / puzzle_id
            puzzle_dir.mkdir(exist_ok=True)

            (puzzle_dir / "puzzle.yaml").write_text(
                yaml.dump(puzzle_data["puzzle"], default_flow_style=False, allow_unicode=True)
            )
            (puzzle_dir / "validate.py").write_text(puzzle_data["validate_py"])
            (puzzle_dir / "solution_stub.py").write_text(puzzle_data["solution_stub_py"])

        # Write NPCs
        for npc_data in data.get("npcs", []):
            npc_id = npc_data.get("id", "")
            if not npc_id:
                continue
            npc_dir = zone_dir / npc_id
            npc_dir.mkdir(exist_ok=True)
            npc_yaml = {k: v for k, v in npc_data.items() if k != "id"}
            (npc_dir / "npc.yaml").write_text(
                yaml.dump(npc_yaml, default_flow_style=False, allow_unicode=True)
            )
