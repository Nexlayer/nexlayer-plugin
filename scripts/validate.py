#!/usr/bin/env python3
"""Validate this plugin before publishing.

Checks:
  1. plugin.json and mcp.json against the vendored Agent Plugins 1.0 schemas
  2. Every skills/<name>/SKILL.md frontmatter against the Agent Skills spec
  3. Every relative link inside skills/ resolves and stays inside the skill
  4. Every nexlayer_* / nexlayerAI_* tool named in the docs exists on the server
  5. Host manifests (.cursor-plugin, .claude-plugin) agree with plugin.json and
     point only at relative in-tree paths that exist

Usage: python3 scripts/validate.py
Exit code 0 = publishable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
SCHEMAS = SCRIPTS / "schemas"

SKILL_NAME = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
TOOL = re.compile(r"\bnexlayer(?:AI)?_[a-z][a-z_]*[a-z]\b")
METADATA_KEYS = {
    "name", "displayName", "version", "description", "homepage",
    "repository", "license", "$schema",
}
PATH_KEYS = {"skills", "commands", "agents", "rules", "logo", "mcpServers", "hooks"}

problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path.relative_to(ROOT)}: missing")
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(ROOT)}: invalid JSON — {exc}")
    return None


def check_schemas() -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        fail("jsonschema not installed — pip install jsonschema (schema checks skipped)")
        return
    for manifest, schema in (("plugin.json", "plugin.schema.json"), ("mcp.json", "mcp.schema.json")):
        doc = load_json(ROOT / manifest)
        sch = load_json(SCHEMAS / schema)
        if doc is None or sch is None:
            continue
        for err in sorted(Draft202012Validator(sch).iter_errors(doc), key=lambda e: list(e.path)):
            fail(f"{manifest} {list(err.path) or '<root>'}: {err.message}")


def check_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("skills/ missing")
        return
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            fail(f"skills/{skill.name}: no SKILL.md")
            continue
        text = md.read_text()
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            fail(f"skills/{skill.name}: SKILL.md has no YAML frontmatter")
            continue
        frontmatter = text[4:].split("\n---\n", 1)[0]
        meta: dict[str, str] = {}
        for line in frontmatter.splitlines():
            match = re.match(r"^([A-Za-z][A-Za-z-]*):\s*(.*)$", line)
            if match:
                meta[match.group(1)] = match.group(2).strip()

        name = meta.get("name", "")
        if not SKILL_NAME.match(name):
            fail(f"skills/{skill.name}: invalid name {name!r}")
        if name != skill.name:
            fail(f"skills/{skill.name}: name {name!r} must match directory")
        desc = meta.get("description", "")
        if not 1 <= len(desc) <= 1024:
            fail(f"skills/{skill.name}: description is {len(desc)} chars (1-1024)")
        if len(meta.get("compatibility", "")) > 500:
            fail(f"skills/{skill.name}: compatibility over 500 chars")

        lines = len(text.splitlines())
        if lines > 500:
            fail(f"skills/{skill.name}: SKILL.md is {lines} lines (keep under 500; move detail to references/)")


REGEX_CHARS = set("{}[]^$|\\*+?()")


def check_links() -> None:
    for md in sorted((ROOT / "skills").rglob("*.md")):
        for link in LINK.findall(md.read_text()):
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if REGEX_CHARS & set(link):
                continue  # regex/code fragment in prose, e.g. a DNS label pattern
            if "/" not in link and "." not in link:
                continue  # not a path reference
            if ".." in Path(link).parts:
                fail(f"{md.relative_to(ROOT)}: link escapes the skill root — {link}")
            if not (md.parent / link).resolve().exists():
                fail(f"{md.relative_to(ROOT)}: dead link {link}")


def check_tool_names() -> None:
    """Catch drift between the shipped docs and the real MCP surface.

    scripts/mcp-tools.txt is generated from the MCP server source — see
    scripts/sync-from-mcp.sh. It is the only thing standing between a typo and a
    skill that tells the agent to call a tool that does not exist.
    """
    listing = SCRIPTS / "mcp-tools.txt"
    if not listing.is_file():
        fail("scripts/mcp-tools.txt missing — cannot verify tool names")
        return
    known = {line.strip() for line in listing.read_text().splitlines() if line.strip()}
    waived = _canon_waivers()
    for doc in sorted(list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.mdc"))):
        if ".git" in doc.parts:
            continue
        text = doc.read_text()
        for name in sorted(set(TOOL.findall(text))):
            if name in known:
                continue
            if f"{name}*" in text or f"{name}_*" in text:  # documented glob, e.g. nexlayer_debug_*
                continue
            if name in waived:
                print(f"  waived: {doc.relative_to(ROOT)} references {name} — {waived[name]}")
                continue
            fail(f"{doc.relative_to(ROOT)}: unknown MCP tool {name}")


def _canon_waivers() -> dict[str, str]:
    """Known defects in the upstream skills, waived so CI stays honest.

    skills/ is a verbatim copy of the MCP repo, so a bad tool name there cannot be
    fixed here — it has to be fixed upstream. Each entry records the reason and is
    removed once the upstream fix lands and is synced.
    """
    path = SCRIPTS / "known-canon-issues.txt"
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, reason = line.partition(" ")
        out[name] = reason.strip(" -") or "no reason recorded"
    return out


def check_host_manifests() -> None:
    portable = load_json(ROOT / "plugin.json") or {}
    for rel in (".cursor-plugin/plugin.json", ".claude-plugin/plugin.json"):
        host = load_json(ROOT / rel)
        if host is None:
            continue
        if host.get("name") != portable.get("name"):
            fail(f"{rel}: name {host.get('name')!r} != plugin.json {portable.get('name')!r}")
        if host.get("version") != portable.get("version"):
            fail(f"{rel}: version {host.get('version')!r} != plugin.json {portable.get('version')!r}")
        for key, value in host.items():
            if key in METADATA_KEYS:
                continue
            candidates = [value] if isinstance(value, str) else (value if isinstance(value, list) else [])
            for candidate in candidates:
                if not isinstance(candidate, str):
                    continue
                if candidate.startswith("/") or ".." in Path(candidate).parts:
                    fail(f"{rel}: {key} must be a relative in-tree path — {candidate}")
                elif key in PATH_KEYS and not (ROOT / candidate.lstrip("./")).exists():
                    fail(f"{rel}: {key} points at missing path {candidate}")

    marketplace = load_json(ROOT / ".claude-plugin/marketplace.json")
    if marketplace:
        names = [p.get("name") for p in marketplace.get("plugins", [])]
        if portable.get("name") not in names:
            fail(f".claude-plugin/marketplace.json: no entry for {portable.get('name')!r}")


def main() -> int:
    check_schemas()
    check_skills()
    check_links()
    check_tool_names()
    check_host_manifests()

    if problems:
        print(f"FAIL — {len(problems)} problem(s):\n")
        for problem in problems:
            print(f"  • {problem}")
        return 1
    print("PASS — manifests, skills, links, tool names, and host manifests all check out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
