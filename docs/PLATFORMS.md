# Platforms

One repository, one payload, thin per-host manifests.

## Why one repo, not one per IDE

Since [Agent Plugins 1.0](https://agent-plugins.org/specification) (August 2026) the portable unit is a directory with `plugin.json`, `skills/`, and `mcp.json`. Cursor, Codex, VS Code, and Copilot read it directly. Claude Code and Grok read a manifest at a different path but load the *same* `skills/`, `commands/`, and `agents/`.

So the per-host difference is three small JSON files, not three codebases:

```
plugin.json                  ← Agent Plugins clients (VS Code, Copilot, Kiro) — skills + MCP
.cursor-plugin/plugin.json   ← Cursor-native: also loads commands/, agents/, rules/
.claude-plugin/plugin.json   ← Claude Code and Grok: commands/, agents/
.codex-plugin/plugin.json    ← Codex: skills + MCP + marketplace listing metadata
                                  ↓  all four point at:
skills/  commands/  agents/  rules/  mcp.json
```

Each host manifest is 20-30 lines of metadata pointing at the same directories. `scripts/validate.py` fails if their `name`/`version` disagree or any path they name is missing, so they cannot drift apart quietly.

A `nexlayer-cursor` / `nexlayer-codex` / `nexlayer-claude-code` split would fork the deployment contract — the part that has to be correct — into N copies that drift. The contract already has one home: the MCP server repo.

## Support matrix

| Client | Manifest it reads | Skills | MCP | Commands | Subagent | Rules | Hooks | Install |
|--------|-------------------|:------:|:---:|:--------:|:--------:|:-----:|:-----:|---------|
| Claude Code | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ➖ | `/plugin marketplace add Nexlayer/nexlayer-plugin` |
| Cursor | `.cursor-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | ✅ | ➖ | Customize → Nexlayer → Install |
| Codex | `.codex-plugin/plugin.json` | ✅ | ✅ | — | — | — | ➖ | `codex plugin marketplace add Nexlayer/nexlayer-plugin` |
| VS Code / Copilot | `plugin.json` | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | Chat: Install Plugin From Source → repo URL |
| Grok | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ➖ | Add repo as a marketplace source, then trust |
| Windsurf | none — MCP only | — | ✅ | — | — | — | — | `mcp.json` snippet from `references/MCP-SETUP.md` |
| Cline / Roo / Kilo | none — MCP only | — | ✅ | — | — | — | — | Same snippet, per-client config path |
| Devin | none — MCP only | — | ✅ | — | — | — | — | Enable Nexlayer in Devin's MCP marketplace |
| Anything else with MCP | none | — | ✅ | — | — | — | — | Point it at `https://mcp.nexlayer.ai/api/mcp` |

✅ shipped · ➖ host supports it, this plugin ships none yet · ⬜ needs the `com.github.copilot/` namespace (see below) · — host has no such concept

**Copilot / VS Code gap.** VS Code reads portable `skills/` and `mcp.json` from the root `plugin.json`, but takes custom agents, slash commands, rules, and hooks *only* from a `com.github.copilot/` directory (`agents/*.agent.md`, `commands/`, `rules/`, `hooks/hooks.json`). Until that directory exists, Copilot users get the tools and the skills but not the commands, the subagent, or the `nexlayer.yaml` rule.

**Hooks gap.** Cursor, Codex, and Copilot all support lifecycle hooks and this plugin ships none. The obvious candidate is validating `nexlayer.yaml` on `afterFileEdit` — worthwhile precisely because the server-side validator misses five documented constraints (see [VALIDATION.md](VALIDATION.md) §6). Event names and payloads differ per host, so it needs one hook script per host and real testing, not a copied `hooks.json`.

Devin has an MCP marketplace, not a plugin format — there is nothing to package for it, and the skills do not transfer. Same for any MCP-only client: they get the tools and none of the judgment.

## Naming

| Thing | Value | Why |
|-------|-------|-----|
| Repo | `Nexlayer/nexlayer-plugin` | Host-agnostic. `nexlayer-cursor-plugin` is wrong the day Codex installs it. |
| Plugin `name` | `nexlayer` | What users type and see. Spec requires lowercase kebab-case. |
| Display name | `Nexlayer` | Marketplace listing. |
| Skill names | `ship-it-nexlayer`, `debug-nexlayer` | Unchanged from the MCP repo, so a skill referenced in a support thread means the same thing everywhere. |
| Commands | `/ship-it-nexlayer`, `/debug-nexlayer` | Match the skills they invoke. |

## Source of truth

`skills/` is copied verbatim from [`Nexlayer/claudecode-mcp-go`](https://github.com/Nexlayer/claudecode-mcp-go) — the same content the server serves through `nexlayer_get_skills`. `scripts/mcp-tools.txt` is generated from that repo's tool registry.

```bash
scripts/sync-from-mcp.sh --check    # drift report
scripts/sync-from-mcp.sh            # resync skills + tool list, then validate
```

Fix skill content upstream, never here — except through `patches/`, which carries small documented corrections for things the shipped docs get wrong while the upstream fix is pending. `sync-from-mcp.sh` reapplies every patch after syncing and exits 3 if one no longer applies, so a patch can never silently rot or be silently reverted. Upstream defects that cannot be fixed from this repo are recorded in `scripts/known-canon-issues.txt`, so the validator stays honest instead of green-by-omission.

## Endpoint

`mcp.json` points at `https://mcp.nexlayer.ai/api/mcp` under the server key `nexlayer-mcp`, matching both `skills/ship-it-nexlayer/references/MCP-SETUP.md` and the public setup docs at [nexlayer.com/docs/mcp](https://nexlayer.com/docs/mcp/overview). The server's own endpoint table lists `/mcp` as primary and `/api/mcp` as a legacy alias; both answer `initialize` today. If `/mcp` becomes the only supported path, change it in both places at once.

## Publishing

### Cursor marketplace

1. `python3 scripts/validate.py` passes.
2. Install from this directory in Cursor, run both commands, confirm the MCP connects and `nexlayer_check_credits` responds.
3. Push to the public repo, tag the release.
4. Submit at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). Manual review, must be open source, every update reviewed before it goes live.

Requirements this repo satisfies: unique lowercase kebab-case name, clear description, valid component frontmatter, logo committed at a relative path (`assets/logo.svg`), documented README, no absolute or parent-escaping paths.

### Claude Code

`.claude-plugin/marketplace.json` is in place, so users can add the repo as a marketplace. Anthropic's official directory is a separate, optional submission.

### Codex

`.codex-plugin/plugin.json` carries the listing metadata (display name, brand color, logo, default prompts) and `.agents/plugins/marketplace.json` makes the repo installable:

```bash
codex plugin marketplace add Nexlayer/nexlayer-plugin
```

Untested against a live Codex install — the marketplace `source.path` is `./` because the plugin sits at the repo root, and `interface.category` is deliberately unset until we know the accepted values.

### VS Code / Copilot

Root `plugin.json` is enough to install: **Chat: Install Plugin From Source** with the repo URL, or search `@agentPlugins` once listed. Commands, agents, and rules need the `com.github.copilot/` namespace described above.

## Release checklist

- [ ] `scripts/sync-from-mcp.sh --check` reports no drift
- [ ] `python3 scripts/validate.py` passes
- [ ] Version bumped in all three manifests (the validator enforces they agree) and in `CHANGELOG.md`
- [ ] Installed and exercised in Cursor and Claude Code against a real deploy
- [ ] Tag pushed

## Open items before submission

- **Docs parity.** The install snippets in the shipped skill now match nexlayer.com/docs/mcp — see docs/VALIDATION.md §8 for what was reconciled and what is still inconsistent on the website side.
- **Public repo is public.** The skills carry migration guidance that names other hosting platforms (`references/MIGRATION.md`, and one line of `SKILL.md`), and a few references mention the underlying orchestration layer. Both are fine internally; decide whether they should ship on a public marketplace page before submitting.
- `Nexlayer/nexlayer-claude-skills` holds an older copy of the deploy skill. Point it here and freeze it.
