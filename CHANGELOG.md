# Changelog

## 1.0.0

First release.

- Agent Plugins 1.0 conformant `plugin.json` — installs in Cursor, Codex, VS Code, and Copilot without per-host packaging
- Nexlayer MCP server over streamable HTTP (`mcp.nexlayer.ai/api/mcp`)
- `nexlayer-deploy` skill: decision tree, service archetypes, networking rules, hard constraints, 24 Dockerfile recipes, 7 known-good `nexlayer.yaml` templates, machine-readable schema
- `nexlayer-debug` skill: read-state-first diagnosis, symptom routing, guardrails on restart/scale/delete
- `nexlayer-ai-sandbox` skill: one-call launches of pre-built AI apps
- Cursor manifest adding three commands, a `nexlayer-deploy` subagent, and a `nexlayer.yaml` rule
- Claude Code manifest and marketplace entry
- `scripts/validate.py` — schema, frontmatter, link, and manifest-consistency checks
