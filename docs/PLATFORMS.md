# Platforms

One repository, one payload, thin per-host manifests. This file records how each client consumes it and why there is no per-platform fork.

## Why one repo

Since [Agent Plugins 1.0](https://agent-plugins.org/specification) (August 2026), the portable unit is a directory with `plugin.json`, `skills/`, and `mcp.json`. Cursor, Codex, VS Code, and Copilot read that directly. Claude Code and Grok read a manifest at a different path but load the *same* `skills/`, `commands/`, and `agents/` directories.

So the differences between hosts are three small JSON files, not three codebases. Forking the plugin per host would mean maintaining the deployment contract — the part that actually has to be correct — in N places, and the copies would drift within a month.

```
plugin.json                  ← Agent Plugins clients (Cursor, Codex, VS Code, Copilot, Kiro)
.cursor-plugin/plugin.json   ← Cursor-native: also loads commands/, agents/, rules/
.claude-plugin/plugin.json   ← Claude Code and Grok
                                  ↓  all three point at:
skills/  commands/  agents/  rules/  mcp.json
```

## Support matrix

| Client | Manifest it reads | Skills | MCP | Commands | Subagent | Rules | Install |
|--------|-------------------|:------:|:---:|:--------:|:--------:|:-----:|---------|
| Cursor | `.cursor-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | ✅ | Customize → Nexlayer → Install |
| Codex | `plugin.json` | ✅ | ✅ | — | — | — | Add repo as a marketplace source |
| VS Code / Copilot | `plugin.json` | ✅ | ✅ | — | — | — | Add repo as a plugin source |
| Claude Code | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | `/plugin marketplace add Nexlayer/nexlayer-plugin` |
| Grok | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | Add repo as a marketplace source, then trust |
| Devin | none — MCP only | — | ✅ | — | — | — | Enable the Nexlayer MCP in Devin's MCP marketplace |
| Anything else with MCP | none | — | ✅ | — | — | — | Point it at `https://mcp.nexlayer.ai/api/mcp` |

Devin has an MCP marketplace, not a plugin format. There is nothing to package for it — the listing is the MCP server, and the skills do not transfer. Same for any client that speaks MCP but has no plugin spec: they get the 50+ tools and none of the judgment.

## Naming

| Thing | Value | Why |
|-------|-------|-----|
| Repo | `Nexlayer/nexlayer-plugin` | Host-agnostic. `nexlayer-cursor-plugin` would be wrong the day Codex installs it. |
| Plugin `name` | `nexlayer` | What users type and see. Spec requires lowercase kebab-case. |
| Display name | `Nexlayer` | Marketplace listing. |
| Skill names | `nexlayer-deploy`, `nexlayer-debug`, `nexlayer-ai-sandbox` | Skill names share a global namespace with every other installed plugin. A bare `deploy` would collide. |
| Commands | `/nexlayer-deploy`, `/nexlayer-debug`, `/nexlayer-sandbox` | Same reason. |

## Publishing

### Cursor marketplace

1. `python3 scripts/validate.py` must pass.
2. Test locally: install from this directory in Cursor, run each command, confirm the MCP connects and `nexlayer_check_credits` responds.
3. Push to the public repo and tag the release (`v1.0.0`).
4. Submit at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). Every plugin is manually reviewed, must be open source, and each update is reviewed before it goes live.

Cursor requirements this repo satisfies: unique lowercase kebab-case name, clear description, valid component frontmatter, logo committed at a relative path (`assets/logo.svg`), documented README, no absolute or parent-escaping paths.

### Claude Code

Users add the repo as a marketplace (`.claude-plugin/marketplace.json` is already in place). Submitting to Anthropic's official directory is a separate, optional step.

### Codex / VS Code

Both read the root `plugin.json`. No extra packaging; add the repo as a marketplace source.

## Release checklist

- [ ] `python3 scripts/validate.py` passes
- [ ] Version bumped in all three manifests (the validator enforces they agree) and in `CHANGELOG.md`
- [ ] Tool names in skills still exist in the live MCP (`nexlayer_get_schema`, `nexlayerAI_list_sandboxes`)
- [ ] Installed and exercised in Cursor and Claude Code against a real deploy
- [ ] Tag pushed

## Consolidation

`Nexlayer/nexlayer-claude-skills` predates this repo and holds an earlier copy of the deploy skill. It should point here and stop taking changes, so the deployment contract lives in exactly one place.
