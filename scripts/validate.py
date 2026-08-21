#!/usr/bin/env python3
"""Validate this plugin before publishing.

Checks:
  1. plugin.json and mcp.json against the vendored Agent Plugins 1.0 schemas
  2. Every skills/<name>/SKILL.md frontmatter against the Agent Skills spec
  3. Host manifests (.cursor-plugin, .claude-plugin) parse and agree on name/version
  4. Every relative link and referenced path inside skills/ resolves
  5. No absolute paths or parent escapes in any manifest path field

Usage: python3 scripts/validate.py
Exit code 0 = publishable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = Path(__file__).resolve().parent / "schemas"

SKILL_NAME = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")

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


def check_links() -> None:
    for md in sorted((ROOT / "skills").rglob("*.md")):
        for link in LINK.findall(md.read_text()):
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (md.parent / link).resolve()
            if not target.exists():
                fail(f"{md.relative_to(ROOT)}: dead link {link}")
            if ".." in Path(link).parts:
                fail(f"{md.relative_to(ROOT)}: link escapes the skill root — {link}")


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
            for candidate in [value] if isinstance(value, str) else (value if isinstance(value, list) else []):
                if not isinstance(candidate, str) or key in {
                    "name", "displayName", "version", "description", "homepage",
                    "repository", "license", "$schema",
                }:
                    continue
                if candidate.startswith("/") or ".." in Path(candidate).parts:
                    fail(f"{rel}: {key} must be a relative in-tree path — {candidate}")
                if key in {"skills", "commands", "agents", "rules", "logo", "mcpServers", "hooks"}:
                    if not (ROOT / candidate.lstrip("./")).exists():
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
    check_host_manifests()

    if problems:
        print(f"FAIL — {len(problems)} problem(s):\n")
        for problem in problems:
            print(f"  • {problem}")
        return 1
    print("PASS — manifests, skills, links, and host manifests all check out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
