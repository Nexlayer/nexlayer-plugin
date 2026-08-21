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
