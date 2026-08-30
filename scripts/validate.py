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
import os
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
PATH_KEYS = {"skills", "commands", "agents", "rules", "logo", "mcpServers", "hooks", "apps"}

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
    for rel in (
        ".cursor-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        ".devin-plugin/plugin.json",
    ):
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

    for rel in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
        marketplace = load_json(ROOT / rel)
        if not marketplace:
            continue
        names = [p.get("name") for p in marketplace.get("plugins", [])]
        if portable.get("name") not in names:
            fail(f"{rel}: no entry for {portable.get('name')!r}")

    # Codex reads interface assets from its own manifest; make sure they exist.
    codex = load_json(ROOT / ".codex-plugin/plugin.json") or {}
    for key, value in (codex.get("interface") or {}).items():
        if key in {"logo", "composerIcon"} and not (ROOT / str(value).lstrip("./")).exists():
            fail(f".codex-plugin/plugin.json: interface.{key} points at missing path {value}")


def check_codex_packaging() -> None:
    """Mirror the Codex plugin ingestion checks that are easy to regress."""
    manifest = load_json(ROOT / ".codex-plugin/plugin.json") or {}
    if not manifest:
        return

    if manifest.get("mcpServers") != "./.mcp.json":
        fail(".codex-plugin/plugin.json: mcpServers must point at ./.mcp.json")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        fail(".codex-plugin/plugin.json: interface must be an object")
    else:
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
        ):
            if not isinstance(interface.get(field), str) or not interface[field].strip():
                fail(f".codex-plugin/plugin.json: interface.{field} is required for Codex")
        prompts = interface.get("defaultPrompt")
        if not isinstance(prompts, list) or not any(
            isinstance(prompt, str) and prompt.strip() for prompt in prompts
        ):
            fail(".codex-plugin/plugin.json: interface.defaultPrompt must include at least one prompt")
        capabilities = interface.get("capabilities")
        if not isinstance(capabilities, list) or not all(
            isinstance(capability, str) and capability.strip() for capability in capabilities
        ):
            fail(".codex-plugin/plugin.json: interface.capabilities must be a non-empty string array")
        for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
            value = interface.get(field)
            if value is not None and not (isinstance(value, str) and value.startswith("https://")):
                fail(f".codex-plugin/plugin.json: interface.{field} must be an https URL")

    mcp = load_json(ROOT / ".mcp.json")
    if mcp is not None:
        extras = set(mcp) - {"mcpServers"}
        for key in sorted(extras):
            fail(f".mcp.json: field {key!r} is not accepted by Codex plugin validation")
        servers = mcp.get("mcpServers")
        if not isinstance(servers, dict) or not servers:
            fail(".mcp.json: mcpServers must be a non-empty object")
        else:
            for name, server in sorted(servers.items()):
                if not isinstance(server, dict):
                    fail(f".mcp.json: server {name!r} must be an object")
                    continue
                if server.get("type") != "streamable-http":
                    fail(f".mcp.json: server {name!r} must use streamable-http")
                url = server.get("url")
                if not isinstance(url, str) or not url.startswith("https://"):
                    fail(f".mcp.json: server {name!r} must use an https URL")

    marketplace = load_json(ROOT / ".agents/plugins/marketplace.json") or {}
    if not marketplace:
        return
    entries = marketplace.get("plugins")
    if not isinstance(entries, list):
        fail(".agents/plugins/marketplace.json: plugins must be an array")
        return
    plugin_name = manifest.get("name")
    matching = [entry for entry in entries if isinstance(entry, dict) and entry.get("name") == plugin_name]
    if not matching:
        fail(f".agents/plugins/marketplace.json: no entry for {plugin_name!r}")
        return
    entry = matching[0]
    if not isinstance(entry.get("category"), str) or not entry["category"].strip():
        fail(".agents/plugins/marketplace.json: plugin entry must include category")
    policy = entry.get("policy")
    if not isinstance(policy, dict):
        fail(".agents/plugins/marketplace.json: plugin entry must include policy")
    else:
        if policy.get("installation") not in {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}:
            fail(".agents/plugins/marketplace.json: policy.installation is invalid")
        if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
            fail(".agents/plugins/marketplace.json: policy.authentication is invalid")
    source = entry.get("source")
    if not isinstance(source, dict):
        fail(".agents/plugins/marketplace.json: plugin entry must include source")
    else:
        rel = source.get("path")
        if source.get("source") != "local":
            fail(".agents/plugins/marketplace.json: source.source must be local")
        if not isinstance(rel, str) or not rel.startswith("./") or ".." in Path(rel).parts:
            fail(".agents/plugins/marketplace.json: source.path must be a ./-prefixed in-tree path")
        elif not (ROOT / rel[2:]).is_dir():
            fail(f".agents/plugins/marketplace.json: source.path points at missing directory {rel}")


def check_generated_mirrors() -> None:
    """Host-namespace copies must match the canonical component they mirror."""
    for src in sorted((ROOT / "agents").glob("*.md")):
        dest = ROOT / "com.github.copilot" / "agents" / f"{src.stem}.agent.md"
        if not dest.is_file():
            fail(f"{dest.relative_to(ROOT)}: missing — run scripts/gen-host-components.py")
        elif dest.read_text() != src.read_text():
            fail(f"{dest.relative_to(ROOT)}: stale — run scripts/gen-host-components.py")


HOOK_SCRIPT = re.compile(r"[\w./${}-]*hooks/([\w.-]+\.(?:py|sh))")


def check_hooks() -> None:
    """Every script a hooks file names must exist and be executable.

    Host hook schemas differ (Cursor's afterFileEdit vs Claude Code's PostToolUse),
    so each host gets its own file; what they must share is a working script.
    """
    for rel in ("hooks/hooks.json", "hooks/claude-code.json"):
        doc = load_json(ROOT / rel)
        if not doc:
            continue
        names = set(HOOK_SCRIPT.findall(json.dumps(doc)))
        if not names:
            fail(f"{rel}: names no hook script")
        for name in sorted(names):
            script = ROOT / "hooks" / name
            if not script.is_file():
                fail(f"{rel}: hook script hooks/{name} not found")
            elif not os.access(script, os.X_OK):
                fail(f"{rel}: hook script hooks/{name} is not executable")


# Verified by installing the plugin and running `claude plugin details`, not read
# off a spec: Claude Code discovers MCP only from a dot-prefixed `.mcp.json` at
# the plugin root. A `mcpServers` path string or inline object in the manifest is
# ignored, and the plugin loads with zero servers while every schema check passes.
# Agent Plugins 1.0 and Cursor want the undotted `mcp.json`, so both must exist
# and agree.
def check_mcp_discovery() -> None:
    dotted, plain = ROOT / ".mcp.json", ROOT / "mcp.json"
    if not dotted.is_file():
        fail(".mcp.json missing — Claude Code loads no MCP server without it")
        return
    # Not a byte comparison: Codex's plugin validator rejects any key but
    # `mcpServers` in .mcp.json, while `mcp.json` carries the Agent Plugins
    # `$schema`. Compare the server map, which is the part that must not drift.
    a = (load_json(plain) or {}).get("mcpServers")
    b = (load_json(dotted) or {}).get("mcpServers")
    if a != b:
        fail(".mcp.json and mcp.json declare different mcpServers")


# Same method, same surprise: Claude Code silently drops a hook whose `command`
# is a list. Every working plugin in the official marketplace uses one shell
# string. Cursor's file additionally requires a top-level `version`.
def check_hook_schemas() -> None:
    doc = load_json(ROOT / "hooks/claude-code.json") or {}
    for event, entries in doc.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if not isinstance(hook.get("command"), str):
                    fail(
                        f"hooks/claude-code.json: {event} command must be one "
                        f"shell string; a list is silently ignored"
                    )

    cursor = load_json(ROOT / "hooks/hooks.json") or {}
    if cursor.get("version") != 1:
        fail('hooks/hooks.json: Cursor requires a top-level "version": 1')
    stray = set(cursor.get("hooks", {})) & {"PostToolUse", "PreToolUse", "Stop"}
    if stray:
        fail(f"hooks/hooks.json: Claude Code event(s) {sorted(stray)} in Cursor's file")


def main() -> int:
    check_schemas()
    check_mcp_discovery()
    check_hook_schemas()
    check_generated_mirrors()
    check_hooks()
    check_skills()
    check_links()
    check_tool_names()
    check_host_manifests()
    check_codex_packaging()

    if problems:
        print(f"FAIL — {len(problems)} problem(s):\n")
        for problem in problems:
            print(f"  • {problem}")
        return 1
    print("PASS — manifests, skills, links, tool names, and host manifests all check out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
