# Nexlayer Plugin

**Ship your app to a live URL from inside your coding agent.**

The official [Nexlayer](https://nexlayer.com) plugin. It gives your agent the Nexlayer MCP server plus three skills: deploy anything containerized, debug it when it breaks, and launch pre-built AI apps with no code at all.

One plugin, every agent. It follows the [Agent Plugins 1.0](https://agent-plugins.org) standard, so the same directory installs in Cursor, Codex, VS Code, Claude Code, and any other client that reads the spec.

```
"deploy this"  →  Dockerfile → image → nexlayer.yaml → validated → live at https://<app>.nexlayer.ai
```

## What you get

| Component | What it does |
|-----------|--------------|
| `nexlayer` MCP server | Deploy, build, push, validate, inspect logs and events, open a shell, query a live database, manage domains and keys |
| `nexlayer-deploy` skill | The deployment contract — decision tree, service archetypes, networking rules, 24 Dockerfile recipes, known-good YAML templates |
| `nexlayer-debug` skill | Crash loops, failed image pulls, unreachable URLs, databases that will not initialize — read state first, then fix the cause |
| `nexlayer-ai-sandbox` skill | One-call launches of pre-built AI apps: chatbot, code reviewer, code copilot, multi-agent workspace, translation hub, content moderation |

Clients that support them also pick up three commands (`/nexlayer-deploy`, `/nexlayer-debug`, `/nexlayer-sandbox`), a `nexlayer-deploy` subagent, and a rule that guards edits to `nexlayer.yaml`.

## Install

### Cursor

Open **Customize** in the sidebar, find **Nexlayer**, select **Install**, and choose project or user scope.

### Claude Code

```bash
/plugin marketplace add Nexlayer/nexlayer-plugin
/plugin install nexlayer@nexlayer
```

### Codex, VS Code, and other Agent Plugins clients

Add this repository as a plugin source in the client's marketplace or plugin settings. The root `plugin.json` is spec-conformant, so no per-client packaging is needed.

### Anything with MCP but no plugin support

Point the client at the MCP server directly:

```json
{
  "mcpServers": {
    "nexlayer": { "type": "streamable-http", "url": "https://mcp.nexlayer.ai/api/mcp" }
  }
}
```

You lose the skills, but the tools all work. See [docs/PLATFORMS.md](docs/PLATFORMS.md) for per-client detail.

## First run

1. Install the plugin and reload the client.
2. Ask your agent to run `nexlayer_check_credits`. It will walk you through sign-in if you are not authenticated.
3. Say *"deploy this"* in any repo.

## Repository layout

```
plugin.json                   Agent Plugins 1.0 manifest (portable core)
mcp.json                      Nexlayer MCP server
skills/                       nexlayer-deploy, nexlayer-debug, nexlayer-ai-sandbox
commands/                     Slash commands (clients that support them)
agents/                       nexlayer-deploy subagent
rules/                        nexlayer.yaml guardrails
.cursor-plugin/plugin.json    Cursor manifest — adds commands, agents, rules
.claude-plugin/               Claude Code manifest and marketplace entry
docs/PLATFORMS.md             Per-client install and support matrix
```

The payload lives once, at the root. Host manifests are thin pointers at the same files — there is no per-platform fork of the skills.

## Contributing

Skills are plain Markdown. Edit `skills/<name>/SKILL.md`, keep it under 500 lines, and move detail into `references/`. Run the checks before opening a PR:

```bash
python3 scripts/validate.py
```

## Links

- [Nexlayer](https://nexlayer.com)
- [Agent Plugins specification](https://agent-plugins.org/specification)
- [Agent Skills specification](https://agentskills.io/specification)

MIT licensed. Issues and PRs welcome.
