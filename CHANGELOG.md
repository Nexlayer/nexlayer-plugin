# Changelog

## 1.0.0

First release.

- Agent Plugins 1.0 conformant `plugin.json` — installs in Cursor, Codex, VS Code, and Copilot with no per-host packaging
- Nexlayer MCP server over streamable HTTP (59 tools)
- `ship-it-nexlayer` skill v3.0.0 and `debug-nexlayer` skill v1.1.0, copied verbatim from `Nexlayer/claudecode-mcp-go` (commit 0f5cc32) with their references, examples, and schema
- Cursor manifest adding two commands, a `nexlayer-deploy` subagent, and a `nexlayer.yaml` rule
- Claude Code manifest and marketplace entry
- `scripts/sync-from-mcp.sh` — resync or drift-check skills and the tool list against the MCP repo
- `scripts/validate.py` — spec schemas, skill frontmatter, links, MCP tool names, manifest agreement

## Unreleased

- `references/MCP-SETUP.md` corrected via `patches/0001`: dashboard is `app.nexlayer.com` (there is no `app.nexlayer.io`), transport is `http` not the deprecated `sse`, Cursor config path is `~/.cursor/mcp.json`, and Claude Code leads with `npx @nexlayer/mcp-install` — all matching nexlayer.com/docs/mcp. Upstream: claudecode-mcp-go#45
- MCP server registered as `nexlayer-mcp`, the same name the public docs and the skill use
- `patches/` layer added: `sync-from-mcp.sh` reapplies patches with `git apply` after every sync and exits 3 if one goes stale, so a local fix can neither rot nor be silently reverted
