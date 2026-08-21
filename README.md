# Nexlayer Plugin

**Ship your app to a live URL from inside your coding agent.**

The official [Nexlayer](https://nexlayer.com) plugin: the Nexlayer MCP server plus the two skills that teach an agent how to deploy on it and how to debug what it deployed.

One plugin, every agent. It follows the [Agent Plugins 1.0](https://agent-plugins.org) standard, so the same directory installs in Cursor, Codex, VS Code, and Claude Code.

```
"deploy this"  →  Dockerfile → image → nexlayer.yaml → validated → live URL
```

## What you get

| Component | What it does |
|-----------|--------------|
| `nexlayer` MCP server | 59 tools: build and push images, validate and deploy YAML, read status/logs/events, exec into pods, edit files, query databases, restart and scale, manage domains, keys, and billing |
| `ship-it-nexlayer` skill | The deployment contract — decision tree, hard constraints, `.pod` vs `<% URL %>` rules, steps 0-10, plus 9 deep references, 18 worked YAML examples, and the machine-readable schema |
| `debug-nexlayer` skill | Live-deployment debugging — proxy session rules, symptom decision tree, and the order to call the debug tools in |

Clients that support them also pick up two commands (`/ship-it-nexlayer`, `/debug-nexlayer`), a `nexlayer-deploy` subagent, and a rule that guards edits to `nexlayer.yaml`.

## Install

### Cursor

Open **Customize** in the sidebar, find **Nexlayer**, select **Install**, and choose project or user scope.

### Claude Code

```bash
/plugin marketplace add Nexlayer/nexlayer-plugin
/plugin install nexlayer@nexlayer
```

### Codex, VS Code, and other Agent Plugins clients

Add this repository as a plugin source. The root `plugin.json` is spec-conformant, so there is no per-client packaging.

### Anything with MCP but no plugin support

Point the client at the server directly:

```json
{
  "mcpServers": {
    "nexlayer": { "type": "streamable-http", "url": "https://mcp.nexlayer.ai/api/mcp" }
  }
}
```

You get the tools, not the skills. See [docs/PLATFORMS.md](docs/PLATFORMS.md) for the full matrix.

## First run

1. Install the plugin and reload the client.
2. Ask your agent to run `nexlayer_check_credits` — it walks you through sign-in if needed.
3. Say *"deploy this"* in any repo.

## Where the skills come from

`skills/` is a **verbatim copy** of `skills/` in [`Nexlayer/claudecode-mcp-go`](https://github.com/Nexlayer/claudecode-mcp-go) — the same content the MCP server serves through `nexlayer_get_skills` and `nexlayer_get_skill_content`. That repo is the source of truth.

Do not hand-edit anything under `skills/` here. Edit it upstream, then resync:

```bash
scripts/sync-from-mcp.sh            # pull skills + tool list from the MCP repo
scripts/sync-from-mcp.sh --check    # report drift without changing anything
python3 scripts/validate.py         # schemas, frontmatter, links, tool names, manifests
```

`scripts/mcp-tools.txt` is generated from the server's tool registry, and `validate.py` fails if a shipped doc names a tool the server does not register. Known upstream defects are recorded in `scripts/known-canon-issues.txt` rather than silently patched here.

## Layout

```
plugin.json                   Agent Plugins 1.0 manifest (portable core)
mcp.json                      Nexlayer MCP server
skills/                       ship-it-nexlayer, debug-nexlayer (verbatim from the MCP repo)
commands/ agents/ rules/      Client extensions — thin wrappers over the skills
.cursor-plugin/plugin.json    Cursor manifest
.claude-plugin/               Claude Code manifest and marketplace entry
scripts/                      sync-from-mcp.sh, validate.py, generated tool list
docs/PLATFORMS.md             Per-client support matrix, naming, release runbook
```

MIT licensed.
