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

It *does* catch: uppercase application names, bad volume size units (`10gb`), and `subdomain` without a custom domain.

So a validated file is not a deployable file. This is why the plugin ships `rules/nexlayer-yaml.mdc` — the constraints have to be enforced while the file is being written, because validation will not catch them and the deploy will fail later. Treat "VALID" as necessary, never sufficient.

## 7. Endpoint and domain drift

- `mcp.json` uses `https://mcp.nexlayer.ai/api/mcp`, which is what `references/MCP-SETUP.md` tells users to configure and what a connected client uses. The server README lists `/mcp` as primary and `/api/mcp` as a legacy alias; both answer `initialize` with 200.
- `references/MCP-SETUP.md` points at `https://app.nexlayer.io` for the dashboard. Live `nexlayer_check_credits` returns `https://app.nexlayer.com/settings/plans`. One of the two is stale — upstream call.
- Canon examples describe deployed app URLs as `*.nexlayer.io` (`your-app.nexlayer.io`, `yourapp.nexlayer.io`). Worth confirming against what the platform actually hands back before this repo goes public.

## Reproducing

```bash
python3 scripts/validate.py                # static checks
scripts/sync-from-mcp.sh --check           # drift vs the MCP repo
```

Then, with the MCP connected: `nexlayer_get_skills` (compare checksums), `nexlayer_get_schema`, `nexlayerAI_list_sandboxes`, and the `nexlayer_validate_yaml` cases in sections 5 and 6.
