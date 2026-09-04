# Patches

`skills/` is a verbatim copy of the MCP server repo. These patches are the *only* sanctioned deviations, applied by `scripts/sync-from-mcp.sh` after every sync. Everything here is temporary by design: each patch exists because a fix is pending upstream, and each one gets deleted the moment the upstream change lands and is synced.

Do not hand-edit files under `skills/`. Change the patch instead, then re-sync — otherwise the next sync silently reverts your edit.

## Why patch at all

A public marketplace listing ships these files to strangers. Where the shipped doc contradicts the live server or the public docs at nexlayer.com, "verbatim" would mean shipping a known-wrong instruction. So the rule is: patch the smallest possible thing, record why, and track the upstream fix.

## Current patches

### `0001-mcp-setup-domain-and-transport.patch`

Target: `skills/ship-it-nexlayer/references/MCP-SETUP.md`
Upstream: [claudecode-mcp-go#45](https://github.com/Nexlayer/claudecode-mcp-go/issues/45)

| Change | Why |
|--------|-----|
| Dashboard `app.nexlayer.io` → `app.nexlayer.com` | `app.nexlayer.io` is not a Nexlayer host. The server's own default is `app.nexlayer.com` (`internal/config/config.go:108`) and live `nexlayer_check_credits` returns `https://app.nexlayer.com/settings/plans`. |
| Claude Code: lead with `npx @nexlayer/mcp-install`, manual path uses `--transport http` | Matches [nexlayer.com/docs/mcp/claude-code](https://nexlayer.com/docs/mcp/claude-code). The doc previously said `--transport sse`; SSE is the deprecated MCP transport. |
| Cursor: config path `~/.cursor/mcp.json`, add `"transport": "http"`, add the green-indicator verification step | Matches [nexlayer.com/docs/mcp/cursor](https://nexlayer.com/docs/mcp/cursor). `.cursor/settings.json` is not where Cursor reads MCP config. |
| Windsurf: add `"transport": "http"` | Consistency with the documented transport. |
| Cline: `"transport": "sse"` → `"http"` | Same deprecated-transport reason. |

Net effect: every install snippet in the shipped skill now agrees with `mcp.json` in this plugin (`streamable-http` to `https://mcp.nexlayer.ai/api/mcp`) and with the public docs.

### `0002-scrub-identifier-and-dead-host.patch`

Targets: `references/BUILD-AND-PUSH.md`, `references/ANTIPATTERNS.md`, `references/ARCHITECTURE-ANTIPATTERNS.md`
Reason: pre-publication review of a repo that is going public.

| Change | Why |
|--------|-----|
| Registry example `user_01kna6j8vrcfj9q0wjtq5qsq3n` → `user_01exampleexampleexample` | The original is a real-shaped account identifier, and it is the namespace component of `registry.nexlayer.io/<userID>/<repo>`. Publishing one gives an attacker a concrete target to probe. The registry itself answers 401 to anonymous requests, so this is defense in depth, not an open door. |
| `[Liz](https://liz.nexlayer.com/)` attribution → plain "Against the Nexlayer MCP schema and live deployments" | `liz.nexlayer.com` does not resolve, so the link is dead, and the line names an internal tool in what becomes public documentation. |

Both should also land upstream so the next sync does not need this patch.

### `0003-scrub-internal-name-and-competitors.patch`

Targets: `SKILL.md`, `references/ANTIPATTERNS.md`, `references/ARCHITECTURE-ANTIPATTERNS.md`
Reason: `SKILL.md` is inlined verbatim into marketplace listings, so its text is public copy, not just agent instructions.

| Change | Why |
|--------|-----|
| `validated: "MCP + Liz verified"` → `"MCP verified"`, and `**Key insight from Liz:**` → `**Key principle:**` in both `ANTIPATTERNS.md` and `ARCHITECTURE-ANTIPATTERNS.md` | `0002` removed the linked form of this attribution; these two unlinked instances survived. Naming an internal tool in public documentation. Matches the `debug-nexlayer` skill, which already says `"MCP verified"`. |
| Decision-tree branch and reference table: named third-party platforms → "another platform" / "another hosting platform" | Cursor and cursor.directory inline `SKILL.md` into the listing body, so these lines become public Nexlayer marketing copy. `references/MIGRATION.md` keeps the names — a migration guide has to name what you are migrating from, and it is not inlined. |

Both should also land upstream so the next sync does not need this patch.

### `0004-allowed-tools-one-pattern-per-token.patch`

Target: `skills/ship-it-nexlayer/SKILL.md` (frontmatter only)
Reason: Agent Skills spec conformance. `allowed-tools` is a space-separated list of `Tool(pattern)` tokens; `Bash(npx:* docker:* git:*)` splits into three malformed tokens.

| Change | Why |
|--------|-----|
| `Bash(npx:* docker:* git:*)` → `Bash(npx:*) Bash(docker:*) Bash(git:*)` | Matches the spec's own example (`Bash(git:*) Bash(jq:*) Read`) and Claude Code's permission-rule syntax. `validate.py` now rejects unbalanced-paren tokens. |

**Ordering:** this patch's context includes the `validated: "MCP verified"` line that `0003` produces, so it applies only after `0003`. `sync-from-mcp.sh` applies patches in filename order, which guarantees that. Keep new patches numbered after any they depend on.

## Adding a patch

```bash
# 1. edit the shipped file under skills/
# 2. regenerate the patch against canon
SRC=/path/to/claudecode-mcp-go
REL=skills/<skill>/<file>
diff -u "$SRC/$REL" "$REL" \
  | sed -e "1s|.*|--- a/$REL|" -e "2s|.*|+++ b/$REL|" \
  > patches/000N-short-name.patch
# 3. document it above with the upstream issue link
# 4. confirm it still applies cleanly
scripts/sync-from-mcp.sh --check
```

## Removing a patch

When the upstream fix is released: delete the `.patch` file, delete its row above, run `scripts/sync-from-mcp.sh`, and confirm the shipped file now matches canon on its own.
