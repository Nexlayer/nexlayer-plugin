# Validation against the live MCP

What this plugin ships was checked against the production Nexlayer MCP server (`https://mcp.nexlayer.ai/api/mcp`), not just against the source repo. Run date: 2026-08-20. Account: Pro, access level full.

Re-run these checks before every release. `scripts/validate.py` covers the static half; this file covers the half that needs a live server.

## 1. Shipped skills are byte-identical to what the server serves

`nexlayer_get_skills` returns a checksum per skill. Those are MD5s of `SKILL.md`:

| Skill | Server checksum | `md5 -q` of shipped file | Match |
|-------|-----------------|--------------------------|:-----:|
| `ship-it-nexlayer` v3.0.0 | `8aac513fe63ea7284c4bbbd06266861a` | `8aac513fe63ea7284c4bbbd06266861a` | ✅ |
| `debug-nexlayer` v1.1.0 | `d76bbefa6a39c5140940ed330b17e8f8` | `d76bbefa6a39c5140940ed330b17e8f8` | ✅ |

The server serves exactly two skills — the two this plugin ships. No extra skill is missing from the bundle.

```bash
md5 -q skills/ship-it-nexlayer/SKILL.md skills/debug-nexlayer/SKILL.md
```

## 2. Reference documents resolve and match

Every name in the SKILL.md reference table was fetched with `nexlayer_get_skill_content`. Spot-checked `MCP-SETUP` and `BUILD-AND-PUSH` against the shipped bytes by content markers (registry format, `oauth2accesstoken`, the Windsurf/Cline sections, the `latest is not allowed` row): all present, no drift.

One reference is *deliberately* not byte-identical: `references/MCP-SETUP.md` carries `patches/0001-mcp-setup-domain-and-transport.patch`. See §8.

## 3. Tool surface

| Source | Count |
|--------|-------|
| `scripts/mcp-tools.txt`, generated from the server's registry + sandbox catalog | 59 |
| Exposed to a connected Pro client | 55 |

The four not exposed — `nexlayer_get_balance`, `nexlayer_initiate_charge`, `nexlayer_open_billing_portal`, `nexlayer_save_card` — are registered in the source but gated at runtime. No shipped doc references any of them, so the generated list stays a safe superset for the validator.

`nexlayerAI_list_sandboxes` returns 6 sandboxes; their `deploy_tool` names match the six `nexlayerAI_deploy_*` entries generated from the catalog slugs exactly.

## 4. Confirmed live: the upstream tool-name defect

`skills/debug-nexlayer/SKILL.md` tells the agent to call `nexlayer_get_deployments` (twice) to resolve `applicationName` from a domain. That tool is **not in the live tool list and not registered anywhere in the server source**. `references/MCP-SETUP.md` also advertises a "List deployments" capability that has no tool behind it.

An agent following the skill will call a tool that does not exist. Tracked in `scripts/known-canon-issues.txt`; needs a fix upstream in `Nexlayer/claudecode-mcp-go`.

## 5. Undocumented v2 schema gate — highest-impact finding

`nexlayer_get_schema` documents `application.version`:

> Set to 2.0 to enable the v2 fields (resources, resourceType, replicas, subdomain). When omitted or set to any other value, those fields are ignored.

The shipped `SKILL.md` documents `resourceType`, `replicas`, and `resources` in its Hard Constraints table, and `LAUNCHFILE-SCHEMA.md` documents them too — **neither mentions the version gate**. Confirmed empirically:

```yaml
# no application.version → validator warns, fields are ignored
pods:
  - name: api
    resourceType: statefulset
    replicas: 3
```
> pod 'api': resourceType, replicas, resources, subdomain require schema version 2.0 but application.version is not set to 2.0 — these fields will be ignored (v1 behavior).

Adding `version: 2.0` makes the same file valid with those fields active. An agent following the skill today writes `resourceType: statefulset` for a database, gets a plain deployment, and nothing tells it. `rules/nexlayer-yaml.mdc` in this plugin now carries the gate; the skill text needs it upstream.

Also confirmed: `subdomain` requires `application.url` — the skill states this correctly, and the validator errors when it is missing.

## 6. What the validator does *not* enforce

Each of these was submitted alone to `nexlayer_validate_yaml` and returned **VALID**, despite the shipped skill listing them as hard constraints:

| Submitted | Skill says | Validator |
|-----------|-----------|-----------|
| `image: nginx` (no tag) | must include `:tag` | VALID |
| no pod with `path` | at least one pod must have `path` | VALID |
| `servicePorts: []` | required, min 1 | VALID |
| pod name `Web_Server` | `^[a-z][a-z0-9-]{1,63}$`, becomes a DNS label | VALID |
| `totallyMadeUpField`, `autoscaleOnVibes` | not in the schema | VALID, silently ignored |

It *does* catch: uppercase application names, bad volume size units (`10gb`), `subdomain` without a custom domain, and `.pod` DNS in a browser-facing variable:

> pod 'web' var 'NEXT_PUBLIC_API_URL': browser-facing variable uses .pod DNS. Browsers cannot resolve .pod hostnames. Use <%URL%> instead.

That last check is the one the skill leans on hardest, and it works. Cosmetic mismatch worth knowing: the validator's message spells the scriptlet `<%URL%>` while the skill and every shipped example use `<% URL %>`. Both deploy; only the error text differs.

So a validated file is not a deployable file. This is why the plugin ships `rules/nexlayer-yaml.mdc` — the constraints have to be enforced while the file is being written, because validation will not catch them and the deploy will fail later. Treat "VALID" as necessary, never sufficient.

## 7. Endpoint and domain drift

- `mcp.json` uses `https://mcp.nexlayer.ai/api/mcp`, which is what `references/MCP-SETUP.md` tells users to configure and what a connected client uses. The server README lists `/mcp` as primary and `/api/mcp` as a legacy alias; both answer `initialize` with 200.
- **Fixed locally:** `references/MCP-SETUP.md` pointed at `https://app.nexlayer.io` for the dashboard. There is no such host — the server's own default is `app.nexlayer.com` (`internal/config/config.go:108`) and live `nexlayer_check_credits` returns `https://app.nexlayer.com/settings/plans`. Patched. Upstream: [claudecode-mcp-go#45](https://github.com/Nexlayer/claudecode-mcp-go/issues/45).
- **Still open upstream:** canon examples describe deployed app URLs as `*.nexlayer.io` in 11 places (`your-app.nexlayer.io`, `abc123.nexlayer.io`, …). `internal/config/config.go:107` defaults `BaseDomain` to `nexlayer.io` but it is env-overridable, and `internal/tools/handlers.go:298-300` treats both `nexlayer.ai` and `nexlayer.io` as managed hosts. Not patched here — it needs someone to confirm what production hands out. Tracked in the same issue.

## 8. Parity with the public docs

Compared the shipped `references/MCP-SETUP.md` against [nexlayer.com/docs/mcp/overview](https://nexlayer.com/docs/mcp/overview), [/claude-code](https://nexlayer.com/docs/mcp/claude-code), and [/cursor](https://nexlayer.com/docs/mcp/cursor).

Agreed already: the server URL `https://mcp.nexlayer.ai/api/mcp` and the server name `nexlayer-mcp`.

Reconciled in `patches/0001`:

| Item | Shipped skill said | Public docs say | Now |
|------|--------------------|-----------------|-----|
| Transport | `--transport sse`, `"transport": "sse"` | `"transport": "http"` | `http` everywhere. SSE is the deprecated MCP transport. |
| Claude Code install | `claude mcp add … --transport sse …` | `npx @nexlayer/mcp-install` | Installer first, manual `claude mcp add … --transport http …` as the fallback. |
| Cursor config path | `.cursor/settings.json` | `~/.cursor/mcp.json` | `~/.cursor/mcp.json`, plus the Settings → Tools & Integrations → MCP verification step. |
| Windsurf / Cline | no transport / `sse` | `http` | `http`. |
| Dashboard | `app.nexlayer.io` | not stated | `app.nexlayer.com` (see §7). |

`mcp.json` in this plugin registers the server as `nexlayer-mcp` — same name the docs and the skill use — over `streamable-http`, which is the Agent Plugins spelling of the same HTTP transport.

Left alone, and worth a look on the website side:

- The overview page says "The MCP server runs locally on your machine." It does not — it is a hosted server at `mcp.nexlayer.ai` reached over HTTP, and auth is SSO/OAuth rather than "your personal API key" as that page also states.
- The overview page lists Zed and JetBrains as fully supported and mentions "VS Code + Continue"; the shipped skill documents Claude Code, Cursor, VS Code + Copilot, Windsurf, and Cline. Neither list is wrong, but they do not match. No Zed or JetBrains snippet was added here — the public docs do not publish one to copy.

## Reproducing

```bash
python3 scripts/validate.py                # static checks
scripts/sync-from-mcp.sh --check           # drift vs the MCP repo
```

Then, with the MCP connected: `nexlayer_get_skills` (compare checksums), `nexlayer_get_schema`, `nexlayerAI_list_sandboxes`, and the `nexlayer_validate_yaml` cases in sections 5 and 6.
