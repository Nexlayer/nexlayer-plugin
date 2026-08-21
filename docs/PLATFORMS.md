# Platforms

One repository, one payload, thin per-host manifests.

## Why one repo, not one per IDE

Since [Agent Plugins 1.0](https://agent-plugins.org/specification) (August 2026) the portable unit is a directory with `plugin.json`, `skills/`, and `mcp.json`. Cursor, Codex, VS Code, and Copilot read it directly. Claude Code and Grok read a manifest at a different path but load the *same* `skills/`, `commands/`, and `agents/`.

So the per-host difference is three small JSON files, not three codebases:

```
plugin.json                  ← Agent Plugins clients (VS Code, Copilot, Kiro, Devin fallback)
.cursor-plugin/plugin.json   ← Cursor: commands/, agents/, rules/, hooks
.claude-plugin/plugin.json   ← Claude Code and Grok: commands/, agents/, hooks
.codex-plugin/plugin.json    ← Codex: skills + MCP + listing metadata
.devin-plugin/plugin.json    ← Devin CLI: skills + MCP + subagents
com.github.copilot/          ← Copilot namespace: agents (the only place VS Code reads them)
                                  ↓  all of them point at:
skills/  commands/  agents/  rules/  hooks/  mcp.json
```

Each host manifest is 20-30 lines of metadata pointing at the same directories. `scripts/validate.py` fails if their `name`/`version` disagree or any path they name is missing, so they cannot drift apart quietly.

A `nexlayer-cursor` / `nexlayer-codex` / `nexlayer-claude-code` split would fork the deployment contract — the part that has to be correct — into N copies that drift. The contract already has one home: the MCP server repo.

## Support matrix

| Client | Manifest it reads | Skills | MCP | Commands | Subagent | Rules | Hooks | Install |
|--------|-------------------|:------:|:---:|:--------:|:--------:|:-----:|:-----:|---------|
| Claude Code | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ✅ | `/plugin marketplace add Nexlayer/nexlayer-plugin` |
| Cursor | `.cursor-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Customize → Nexlayer → Install |
| Codex | `.codex-plugin/plugin.json` | ✅ | ✅ | — | — | — | ➖ | `codex plugin marketplace add Nexlayer/nexlayer-plugin` |
| VS Code / Copilot | `plugin.json` + `com.github.copilot/` | ✅ | ✅ | — | ✅ | — | ➖ | Chat: Install Plugin From Source → repo URL |
| Devin CLI | `.devin-plugin/plugin.json` | ✅ | ✅ | — | ✅ | ✅ | ➖ | `devin plugins install Nexlayer/nexlayer-plugin` |
| Grok | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ✅ | Add repo as a marketplace source, then trust |
| Windsurf | none — MCP only | — | ✅ | — | — | — | — | `mcp.json` snippet from `references/MCP-SETUP.md` |
| Cline / Roo / Kilo | none — MCP only | — | ✅ | — | — | — | — | Same snippet, per-client config path |
| Anything else with MCP | none | — | ✅ | — | — | — | — | Point it at `https://mcp.nexlayer.ai/api/mcp` |

✅ shipped · ➖ host supports it, hook schema not verified yet · — host has no such concept

**Hooks.** `hooks/nexlayer-yaml-check.py` runs on every file edit and checks `nexlayer.yaml` for the things the server-side validator lets through — untagged image, empty `servicePorts`, no pod with `path`, invalid pod name, unknown fields — plus the `version: 2.0` gate, `.pod` in browser-facing vars, loopback addresses, volume-size units, and the Postgres `PGDATA` trap. It is advisory: findings go to stdout, exit code is always 0, and it stays silent on a clean file or an unrelated edit.

Cursor and Claude Code both read `hooks/hooks.json` by default but with **different schemas**, so each gets its own file (`hooks/cursor.json` with `afterFileEdit`, `hooks/claude-code.json` with `PostToolUse` and `${CLAUDE_PLUGIN_ROOT}`) and each manifest points at its own. Codex and Copilot support hooks too; their schemas are not documented well enough to write blind, so they are left off rather than guessed.

**Copilot.** VS Code reads portable `skills/` and `mcp.json` from the root manifest, but custom agents only from `com.github.copilot/agents/*.agent.md`. That file is generated from `agents/` by `scripts/gen-host-components.py`, and `validate.py` fails if it drifts. Copilot CLI's own plugin reference lists agents, skills, hooks, MCP, and LSP — no commands or rules — so nothing is mirrored for those.

**Devin.** Devin CLI shipped plugins (closed beta). It reads `.devin-plugin/plugin.json`, falls back to `.claude-plugin/plugin.json` or the root `plugin.json`, and honors Agent Plugins 1.0 including `${PLUGIN_ROOT}`. It also reads `rules/` and `agents/`, so Devin gets more of this plugin than Codex does.

Devin has an MCP marketplace, not a plugin format — there is nothing to package for it, and the skills do not transfer. Same for any MCP-only client: they get the tools and none of the judgment.

## Naming

| Thing | Value | Why |
|-------|-------|-----|
| Repo | `Nexlayer/nexlayer-plugin` | Host-agnostic. `nexlayer-cursor-plugin` is wrong the day Codex installs it. |
| Plugin `name` | `nexlayer` | What users type and see. Spec requires lowercase kebab-case. |
| Display name | `Nexlayer` | Marketplace listing. |
| Skill names | `ship-it-nexlayer`, `debug-nexlayer` | Unchanged from the MCP repo, so a skill referenced in a support thread means the same thing everywhere. |
| Commands | `/ship-it-nexlayer`, `/debug-nexlayer` | Match the skills they invoke. |

## Is one repo the right shape?

Checked against how other vendors actually ship. Anthropic's official marketplace catalog lists 286 plugins: **150 sit at a repo root, 83 in a subdirectory** of a vendor repo. The recurring pattern is one repo per company, named for the surface rather than the host — `awslabs/agent-plugins` (7 listed plugins), `aws/agent-toolkit-for-aws` (4), `grafana/ai-marketplace` (3), `carta/plugins` (3), `adobe/skills`, `airtable/skills`, `auth0/agent-skills`, `databricks/databricks-agent-skills`, `dropbox/dropbox-ai-plugins`, `canva/canva-skills`, `expo/skills`, `Shopify/liquid-skills`, `microsoft/Dataverse-skills`.

Nobody ships `company-cursor` and `company-claude-code` as separate repos. So one repo is right; the open question was root vs `plugins/<name>/` subdirectory.

**Decision: plugin at the repo root.** Devin (`devin plugins install owner/repo`) and VS Code (*Install Plugin From Source* with a repo URL) resolve a plugin at the repo root, so a subdirectory layout costs compatibility with two of the six targets. Both marketplace files already carry a `plugins[]` array, so if a second plugin ever ships (say a GPU or enterprise bundle), it moves to `plugins/<name>/` then — a mechanical change to path strings, not a re-architecture.

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

`.claude-plugin/marketplace.json` is in place, so users can add the repo as a marketplace directly. For the public community marketplace:

1. `claude plugin validate . --strict` must pass — the review pipeline runs the same check, plus automated safety screening.
2. Submit at [claude.ai/admin-settings/directory/submissions/plugins/new](https://claude.ai/admin-settings/directory/submissions/plugins/new) (Team/Enterprise org with directory access) or [platform.claude.com/plugins/submit](https://platform.claude.com/plugins/submit) for individual authors.
3. Approved plugins are pinned to a commit SHA in `anthropics/claude-plugins-community`, and CI bumps the pin as commits land. The catalog syncs nightly, so listing lags approval.

`claude-plugins-official` is curated by Anthropic at its discretion — there is no application, and the submission form does not add plugins to it.

### Connectors Directory — separate submission, different artifact

The Claude Connectors Directory lists the **MCP server**, not this plugin, and it belongs to `Nexlayer/claudecode-mcp-go`. Its requirements: every tool carries a `title` plus `readOnlyHint` or `destructiveHint` (that repo added the annotations in `annotateAllTools`), OAuth 2.0, a privacy policy, clear setup docs, a support contact, an icon, one to five categories, and a reviewer test account. Submission runs through [claude.ai/admin-settings/directory/submissions/new](https://claude.ai/admin-settings/directory/submissions/new).

Keep the two tracks straight: the connector makes the *tools* discoverable; this plugin makes the *judgment* — the skills, the subagent, the guardrails — installable.

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
