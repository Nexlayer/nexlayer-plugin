# Pre-publication security review

Run before flipping this repository public. Date: 2026-08-21, at commit `1e9ce2a`.

Scope: everything this repo publishes — the working tree **and** the git history, since both become readable at once.

## Clean

| Check | Result |
|-------|--------|
| Literal secrets (`api_key=`, `token=`, `password=` with a real value) | none |
| Key-shaped strings (`sk-`, `ghp_`, `github_pat_`, `eyJhbGciOi…`, `AKIA…`, `xoxb-`) | 10 hits, all obvious placeholders (`sk-1234567890abcdef`, `ghp_xxxxxxxx`, base64 of `{"api_key": "sk-123"}`) |
| Same scan across all 232 blobs in git history | nothing |
| Local machine paths (`/Users/…`, temp dirs) in tree or history | none |
| Private IPs, cluster-internal hostnames (`*.svc`, `*.cluster.local`) | none |
| Anonymous access to `registry.nexlayer.io` | `GET /v2/` → **401**, `GET /v2/_catalog` → **401**. No anonymous enumeration. |
| Server code, deploy credentials, infrastructure manifests | none — this repo is documentation plus one local read-only script |
| GitHub Actions: `pull_request_target`, expression injection, secret usage | none of the three |

## Fixed in this pass

**A real-shaped account identifier.** `references/BUILD-AND-PUSH.md` used `user_01kna6j8vrcfj9q0wjtq5qsq3n` as the registry-path example. That is the namespace component of `registry.nexlayer.io/<userID>/<repo>`, so publishing one hands over a concrete probe target. Replaced with `user_01exampleexampleexample` via `patches/0002`. The registry's 401 means this was defense in depth rather than an open door — but it should be scrubbed upstream too.

**A dead internal-tool link.** Two references carried `[Liz](https://liz.nexlayer.com/)` in their validation header. The host does not resolve (curl → connection failure), and the line names an internal tool in what becomes public documentation. Replaced with a plain attribution.

**Workflow hardening.** The validate workflow now declares `permissions: contents: read`, pins both actions to full commit SHAs, and sets `persist-credentials: false`. Fork pull requests run `validate.py` *from the pull request*, so the token it runs under must be read-only and carry no secrets.

**`.gitignore`.** Added `.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials.json`, `service-account*.json` so a future accident is harder.

**`SECURITY.md`.** Reporting path (support@nexlayer.com, not a public issue), plus an explicit statement of what runs where — useful for a reviewer and for anyone deciding whether to trust the hook.

## Accepted, with reasoning

**The debug skill documents the debug tool surface.** `skills/debug-nexlayer/SKILL.md` explains `deploy_proxy`, `namespace_info`, `proxy_exec`, `shell_open`, and `db_query`. Every one requires an authenticated session and operates inside the caller's own namespace, and any account can already enumerate them through `tools/list`. Documenting usage adds no capability an attacker did not have.

**`scripts/mcp-tools.txt` lists 59 tools; a connected client sees 55.** The four extras (`get_balance`, `initiate_charge`, `open_billing_portal`, `save_card`) are registered server-side but runtime-gated. Publishing the names reveals that billing capabilities exist — low value to an attacker, and the file has to stay complete for the drift check to catch a doc naming a tool that does not exist. Filter it if that trade stops being worth it.

**Examples show plaintext values in `vars:`.** That is deliberate: the YAML shape has to be readable. `SECURITY.md` now states that real deployments put sensitive values in `secrets:`, and every example value is a placeholder.

**Git history contains superseded drafts.** Nine commits of iteration are recoverable once public, including an earlier skill variant with instructions that are now wrong (it predated the canon rebuild). Nothing sensitive, but if a clean single-commit history is preferred for a public launch, squash before flipping visibility — after, it is too late.

## For the platform team, not this repo

**`nexlayer_build_and_push_image` returns the user's session JWT** as the registry password. `BUILD-AND-PUSH.md` correctly says to pass it via `--password-stdin` so it misses shell history — but the token still lands in the agent's context window, its transcript, and whatever the host logs. That is a real credential-handling question for an agent-facing tool. Options worth considering: a short-lived registry-scoped token instead of the session JWT, or having the tool return a login command that fetches the token itself. Not verifiable or fixable from this repo.

**Namespace scoping of the debug proxy** is worth confirming server-side: the client passes a `domain` and `applicationName`, and the skill warns that an unscoped session "dumps all pods in the namespace." If that scoping is enforced only by the client-supplied arguments rather than by the authenticated identity, it would be an access-control issue. **Not tested** — probing another tenant's namespace would be unauthorized. Confirm in `claudecode-mcp-go`.

## Before flipping to public

- [ ] Decide the competitor-name question: `references/MIGRATION.md` names other hosting platforms 75 times, plus 1 line in `SKILL.md` and 4 in `speed-stack.yaml`
- [ ] Decide the orchestration-layer question: 9 mentions across `ARCHITECTURE-ANTIPATTERNS.md`, `LAUNCHFILE-SCHEMA.md`, and the schema
- [ ] Settle the `*.nexlayer.io` vs `*.nexlayer.ai` app-URL question in the 11 examples ([claudecode-mcp-go#45](https://github.com/Nexlayer/claudecode-mcp-go/issues/45)) — publishing the wrong host teaches every reader something false
- [ ] `skills/debug-nexlayer/SKILL.md` references `happy-tiger.nexlayer.app`, a domain shape that is not in use
- [ ] Squash history first if a clean public timeline matters
- [ ] Enable branch protection on `main` and require the validate workflow, so a public fork's PR cannot land unchecked

## Reproducing

```bash
# secrets in the tree
grep -rniE "(api[_-]?key|secret|token|password)['\"]?\s*[:=]\s*['\"][^'\"<{$]{8,}" .
# secrets in history
git rev-list --objects --all | awk '{print $1}' | while read o; do \
  [ "$(git cat-file -t $o)" = blob ] && git cat-file -p $o; done \
  | grep -aoE "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|eyJhbGciOi[A-Za-z0-9_-]{10,}|AKIA[0-9A-Z]{16})"
# registry must reject anonymous callers
curl -s -o /dev/null -w "%{http_code}\n" https://registry.nexlayer.io/v2/
```
