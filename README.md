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
| `nexlayer` MCP server | 55 tools: build and push images, validate and deploy YAML, read status/logs/events, exec into pods, edit files, query databases, restart and scale, manage domains, keys, and billing |
| `ship-it-nexlayer` skill | The deployment contract — decision tree, hard constraints, `.pod` vs `<% URL %>` rules, steps 0-10, plus 9 deep references, 18 worked YAML examples, and the machine-readable schema |
| `debug-nexlayer` skill | Live-deployment debugging — proxy session rules, symptom decision tree, and the order to call the debug tools in |

Clients that support them also pick up two commands (`/ship-it-nexlayer`, `/debug-nexlayer`), a `nexlayer-deploy` subagent, a rule that guards edits to `nexlayer.yaml`, and a file-edit hook that checks `nexlayer.yaml` for the mistakes the server-side validator lets through.

## Install

### Cursor

Open **Customize** in the sidebar, find **Nexlayer**, select **Install**, and choose project or user scope.

### Claude Code

```bash
/plugin marketplace add Nexlayer/nexlayer-plugin
/plugin install nexlayer@nexlayer
```

### Codex

```bash
codex plugin marketplace add Nexlayer/nexlayer-plugin
```

### VS Code / GitHub Copilot

Command Palette → **Chat: Install Plugin From Source** → this repo's URL. The root `plugin.json` is spec-conformant, so skills, tools, and the subagent load with no extra setup.

### Devin CLI

```bash
devin plugins install Nexlayer/nexlayer-plugin
```

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

Do not hand-edit anything under `skills/` here. Edit it upstream, then resync. The one sanctioned exception is `patches/`, which holds small documented fixes for things that are wrong in the shipped docs and pending upstream — `sync-from-mcp.sh` reapplies them after every sync and fails loudly if one goes stale. See [patches/README.md](patches/README.md).

```bash
scripts/sync-from-mcp.sh            # pull skills + tool list from the MCP repo
scripts/sync-from-mcp.sh --check    # report drift without changing anything
scripts/gen-host-components.py      # regenerate host-namespace mirrors
python3 scripts/validate.py         # schemas, frontmatter, links, tool names, manifests, hooks
claude plugin validate . --strict   # Anthropic's own gate, run by their review pipeline
```

The bundle is also tested against the production MCP server, not just the source repo — shipped skill checksums, the tool surface, the schema, and the validator's real behavior. See [docs/VALIDATION.md](docs/VALIDATION.md).

`scripts/mcp-tools.txt` is generated from the server's tool registry, and `validate.py` fails if a shipped doc names a tool the server does not register. Known upstream defects are recorded in `scripts/known-canon-issues.txt` rather than silently patched here.

## Layout

```
plugin.json                   Agent Plugins 1.0 manifest (portable core)
mcp.json                      Nexlayer MCP server
skills/                       ship-it-nexlayer, debug-nexlayer (verbatim from the MCP repo)
commands/ agents/ rules/      Client extensions — thin wrappers over the skills
.cursor-plugin/plugin.json    Cursor manifest
.claude-plugin/               Claude Code manifest and marketplace entry
.codex-plugin/plugin.json     Codex manifest and listing metadata
.agents/plugins/              Codex marketplace entry
hooks/                        nexlayer.yaml checker + per-host hook config
com.github.copilot/           Copilot namespace (generated mirror of agents/)
patches/                      Documented deviations from canon, reapplied on every sync
scripts/                      sync-from-mcp.sh, validate.py, generated tool list
docs/PLATFORMS.md             Per-client support matrix, naming, release runbook
docs/VALIDATION.md            Results of testing the bundle against the live MCP
docs/SECURITY-REVIEW.md       Pre-publication security review
```

MIT licensed. Security reports go to support@nexlayer.com — see [SECURITY.md](SECURITY.md).
