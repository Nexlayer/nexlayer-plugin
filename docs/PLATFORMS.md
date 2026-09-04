# Platforms

One repository, one payload, thin per-host manifests.

## Why one repo, not one per IDE

Since [Agent Plugins 1.0](https://agent-plugins.org/specification) (August 2026) the portable unit is a directory with `plugin.json`, `skills/`, and `mcp.json`. VS Code, Copilot, and Devin fallback read it directly. Cursor, Codex, Claude Code, and Grok read a manifest at a host-specific path but load the *same* `skills/`, `commands/`, and `agents/`.

So the per-host difference is three small JSON files, not three codebases:

```
plugin.json                  ← Agent Plugins clients (VS Code, Copilot, Kiro, Devin fallback)
.cursor-plugin/plugin.json   ← Cursor: commands/, agents/, rules/, hooks
.claude-plugin/plugin.json   ← Claude Code and Grok: commands/, agents/, hooks
.codex-plugin/plugin.json    ← Codex: skills + MCP + listing metadata
.devin-plugin/plugin.json    ← Devin CLI: skills + MCP + subagents
com.github.copilot/          ← Copilot namespace: agents (the only place VS Code reads them)
                                  ↓  all of them point at:
skills/  commands/  agents/  rules/  hooks/  mcp.json  .mcp.json
```

Each host manifest is 20-30 lines of metadata pointing at the same directories. `scripts/validate.py` fails if their `name`/`version` disagree or any path they name is missing, so they cannot drift apart quietly.

A `nexlayer-cursor` / `nexlayer-codex` / `nexlayer-claude-code` split would fork the deployment contract — the part that has to be correct — into N copies that drift. The contract already has one home: the MCP server repo.

## Support matrix

| Client | Manifest it reads | Skills | MCP | Commands | Subagent | Rules | Hooks | Install |
|--------|-------------------|:------:|:---:|:--------:|:--------:|:-----:|:-----:|---------|
| Claude Code | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ✅ | `/plugin marketplace add Nexlayer/nexlayer-plugin` |
| Cursor | `.cursor-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Customize → Nexlayer → Install |
| Codex | `.codex-plugin/plugin.json` | ✅ | ✅ | — | — | — | ✅ | `codex plugin marketplace add Nexlayer/nexlayer-plugin` |
| VS Code / Copilot | `plugin.json` + `com.github.copilot/` | ✅ | ✅ | — | ✅ | — | ➖ | Chat: Install Plugin From Source → repo URL |
| Devin CLI | `.devin-plugin/plugin.json` | ✅ | ✅ | — | ✅ | ✅ | — | `devin plugins install Nexlayer/nexlayer-plugin` |
| Grok | `.claude-plugin/plugin.json` | ✅ | ✅ | ✅ | ✅ | — | ✅ | Add repo as a marketplace source, then trust |
| Windsurf | none — MCP only | — | ✅ | — | — | — | — | `mcp.json` snippet from `references/MCP-SETUP.md` |
| Cline / Roo / Kilo | none — MCP only | — | ✅ | — | — | — | — | Same snippet, per-client config path |
| Anything else with MCP | none | — | ✅ | — | — | — | — | Point it at `https://mcp.nexlayer.ai/api/mcp` |

✅ shipped · ➖ host supports it, plugin-root variable for the hook command not documented, so left off · — host has no such concept or reads a location this repo does not ship

Only Claude Code has been exercised by a live install (see the loading-rules section below and `docs/VALIDATION.md`). Codex was exercised by the Codex plugin validator and an isolated `CODEX_HOME` install. Cursor, VS Code, Devin, and Grok are conformance-by-documentation.

**Hooks.** `hooks/nexlayer-yaml-check.py` runs after a file edit and checks `nexlayer.yaml` for the things the server-side validator lets through — untagged image, empty `servicePorts`, no pod with `path`, invalid pod name, unknown fields — plus the `version: 2.0` gate, `.pod` in browser-facing vars, loopback addresses, volume-size units, and the Postgres `PGDATA` trap. It is advisory: findings go to stdout, exit code is always 0, and it stays silent on a clean file or an unrelated edit. It walks every string in whatever JSON the host sends, so it finds the path in Claude Code's `tool_input.file_path`, Cursor's `file_path`, Codex's `apply_patch` patch text (resolved against `cwd`), and Copilot's `toolArgs`.

Three hosts default to the same filename with two schemas, so the layout is:

| File | Schema | Read by | How |
|------|--------|---------|-----|
| `hooks/hooks.json` | nested — `PostToolUse` → `matcher` → `hooks[]` with one shell-string `command` using `${CLAUDE_PLUGIN_ROOT}` | Claude Code, Codex | Both default to this path. Claude Code reads it **even when the manifest points elsewhere** (verified from a `--debug` session), so it has to be in this schema. Codex provides `CLAUDE_PLUGIN_ROOT` as an alias of `PLUGIN_ROOT`. Matcher covers Claude Code's `Write|Edit|MultiEdit|NotebookEdit` and Codex's `apply_patch`. |
| `hooks/cursor.json` | flat — `"version": 1`, `afterFileEdit` → `command` | Cursor | `.cursor-plugin/plugin.json` points at it. Cursor's docs are explicit that a manifest `hooks` field replaces default discovery. The command is a plugin-relative script path, the form Cursor's own examples use; `${CURSOR_PLUGIN_ROOT}` is the documented alternative if the live install shows the relative path resolving elsewhere. |

The cost of this split is that community scanners that look only for `hooks/hooks.json` (cursor.directory) will report a `PostToolUse` hook rather than Cursor's `afterFileEdit`. Cursor itself reads the manifest. The previous layout — Cursor's schema at the default name — produced `[WARN] hooks.afterFileEdit: unknown hook event` on every Claude Code session start for every user.

**Loading rules that no schema check catches.** Each was found by installing the plugin and inspecting `claude plugin details` or a `--debug` session log, and each is now enforced by `scripts/validate.py`:

| Rule | Wrong form | Symptom |
|------|-----------|---------|
| Claude Code discovers MCP only from a dot-prefixed `.mcp.json` at the plugin root | `mcp.json` + `"mcpServers": "./mcp.json"`, or an inline object | `MCP servers (0)` |
| A hook `command` must be one shell string | `["python3", "..."]` | `Hooks (0)` |
| Claude Code reads `hooks/hooks.json` regardless of the manifest `hooks` pointer | Cursor's schema at the default name | `WARN unknown hook event` every session |
| Claude Code treats `commands/` as deprecated and also exposes each skill as a slash command | `commands/` + `skills/` with the same names | `Skills (4)` with duplicate names; `"commands": []` in `.claude-plugin/plugin.json` suppresses the deprecated dir |
| Claude Code dedupes a plugin MCP server against a manually-configured server with the same URL | — | `Suppressing plugin MCP server … duplicates manually-configured` — correct behaviour, and why a developer machine with the server in `~/.claude.json` will not show the plugin's copy |
| Codex's validator rejects any key but `mcpServers` in `.mcp.json` | `$schema` in `.mcp.json` | Codex validation fails |
| Cursor, Claude Code, Codex, and Agent Plugins all want manifest paths to start with `./` | `"skills": "skills"` | Undefined per host; normalised everywhere |

So the repo ships **both** `mcp.json` (Agent Plugins 1.0, Cursor, VS Code) and `.mcp.json` (Claude Code, Codex, Devin, Copilot CLI) with the same `mcpServers` map; the dotted file omits `$schema`. `validate.py` compares the maps rather than the bytes.

**Transport type.** Both files declare `"type": "streamable-http"`, the Agent Plugins 1.0 value. Claude Code accepts it and normalises to HTTP (verified: a project `.mcp.json` with both `streamable-http` and `http` lists both as `(HTTP)`). Cursor's native remote-server shape is `{"url": …}` with no `type`; whether Cursor's plugin loader tolerates the extra key is unverified until a live install.

**Windows.** The hook is a Python 3 script. Claude Code and Codex invoke it as `python3 "${CLAUDE_PLUGIN_ROOT}/…"`, which needs `python3` on `PATH` — present with the Microsoft Store Python, absent by default with the python.org installer, which ships `python` and `py`. Cursor invokes it by path, which relies on the shebang and does not work on Windows outside a POSIX shell. Cursor's own hook examples have the same property. Because the hook is advisory and exits 0, a Windows user loses the pre-deploy warnings and nothing else. Copilot's hook schema has separate `bash` and `powershell` commands — the only host that solves this — and is recorded below for when a plugin-root variable is confirmed for it.

**Copilot.** VS Code auto-detects the format from the root manifest: a `plugin.json` carrying the Agent Plugins `$schema` is read as Agent Plugins 1.0, so skills come from `skills/`, MCP from `mcp.json`, and Copilot-specific content from `com.github.copilot/` — which VS Code documents as holding `agents/`, `hooks/`, `commands/`, and `rules/`. Custom agents are `com.github.copilot/agents/*.agent.md` (frontmatter `name`, `description`, optional `tools`), generated from `agents/` by `scripts/gen-host-components.py` and drift-checked by `validate.py`. `commands/` and `rules/` are not mirrored: VS Code's native formats there are `.prompt.md` and `.instructions.md` with `applyTo`, not the `.md`/`.mdc` this repo carries, and a wrong-format mirror is worse than none. Copilot CLI hooks are `{"version": 1, "hooks": {"postToolUse": [{"type": "command", "bash": "…", "powershell": "…"}]}}` with a camelCase `toolArgs` payload — schema verified, but no documented plugin-root variable for the command, so not shipped.

**Devin.** Devin CLI shipped plugins (closed beta). It reads `.devin-plugin/plugin.json`, falls back to `.claude-plugin/plugin.json` or the root `plugin.json`, and honors Agent Plugins 1.0 including `${PLUGIN_ROOT}`. Documented manifest keys are the metadata set plus `skills`, `mcpServers`, `requiredPlugins`, `optionalPlugins`, `forbiddenPlugins` — `validate.py` rejects anything else, which is why the earlier `agentSubagents` key was dropped; Devin reads `agents/<name>.md` by convention. MCP precedence is `.mcp.json`, then `mcp.json`, then manifest paths. Devin reads hooks from `hooks.json` at the plugin **root**, not `hooks/`, so it gets no hook from this repo; its `rules/` use Windsurf-style trigger frontmatter, so `rules/nexlayer-yaml.mdc` (Cursor frontmatter) may load without its glob trigger.

A client with an MCP marketplace but no plugin format has nothing here to package: the skills do not transfer, so it gets the tools and none of the judgment. That is the whole Windsurf / Cline / Roo / Kilo row above.

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

`mcp.json` and `.mcp.json` point at `https://mcp.nexlayer.ai/api/mcp` under the server key `nexlayer-mcp`, matching both `skills/ship-it-nexlayer/references/MCP-SETUP.md` and the public setup docs at [nexlayer.com/docs/mcp](https://nexlayer.com/docs/mcp/overview). The server's own endpoint table lists `/mcp` as primary and `/api/mcp` as a legacy alias; both answer `initialize` today. If `/mcp` becomes the only supported path, change it in both places at once.

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

`.codex-plugin/plugin.json` carries the listing metadata (display name, category, brand color, legal URLs, logo, default prompts) and `.agents/plugins/marketplace.json` makes the repo installable:

```bash
codex plugin marketplace add Nexlayer/nexlayer-plugin
```

The marketplace `source.path` is `./` because the plugin sits at the repo root. This layout was tested with `codex plugin marketplace add <repo-path>` and `codex plugin add nexlayer@nexlayer`; Codex resolved the plugin source to the repository root.

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
- **Public repo is public.** Resolved for the listing surface: marketplace scanners inline `SKILL.md` verbatim into the listing body, so `patches/0003` neutralizes the named platforms there. `references/MIGRATION.md` keeps them deliberately — a migration guide has to name what you migrate from, and references are not inlined. Still open: a few references describe resource limits in the underlying orchestration layer's units, which is factually required by the field but reads as implementation detail.
- `Nexlayer/nexlayer-claude-skills` holds an older copy of the deploy skill. Point it here and freeze it.
