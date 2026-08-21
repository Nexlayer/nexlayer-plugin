---
name: nexlayer-debug
description: Diagnose and fix a Nexlayer app that is already deployed — crash loops, failed image pulls, a service that will not start, a database that will not initialize, a frontend that cannot reach its API, 502s, or a URL that returns nothing. Also use to read logs, events, and status, open a shell in a running service, or query a live database. Trigger when the user says their Nexlayer deployment is broken, stuck, unhealthy, erroring, or "was working yesterday".
license: MIT
compatibility: Requires the Nexlayer MCP server (mcp.nexlayer.ai)
metadata:
  author: nexlayer
  version: "2.1.0"
allowed-tools: Read
---

# Nexlayer Debug

Fix a deployment that already exists. To create a new one, use the `nexlayer-deploy` skill instead.

## Rule Zero: never guess, never blind-sweep

Read state before changing state. Diagnosis is free; restarts, scales, and deletes are not.

| Never | Instead |
|-------|---------|
| Restart a service to "see if it helps" | Read logs and events first, then restart with a stated reason |
| Run a destructive tool with empty/default args | Name the exact app and service every call |
| Scale, restart, or delete without telling the user | State what you are about to change and why, then do it |
| Delete a deployment to fix a bad config | Fix the YAML and redeploy — deletes are not recoverable |

`nexlayer_delete_deployment`, `nexlayer_debug_pod_restart`, `nexlayer_debug_pod_restart_deployment`, and `nexlayer_debug_pod_scale` change production. Confirm with the user before the first one in a session.

## Step 1 — Establish the facts (always, in this order)

```
1. nexlayer_check_deployment_status   → which services are up, which are not
2. nexlayer_get_deployment_logs       → what the failing service printed
3. nexlayer_get_deployment_events     → what the platform did (pulls, scheduling, health checks)
```

Only after those three do you form a hypothesis.

## Step 2 — Route on the symptom

| Symptom | Most likely cause | Go to |
|---------|-------------------|-------|
| `ImagePullBackOff` / `ErrImagePull` | Wrong image name/tag, wrong platform, private registry creds | references/TROUBLESHOOT.md → Image Issues |
| `CrashLoopBackOff` | App exits on boot — usually a bad env var or `localhost` | references/TROUBLESHOOT.md → Application Crashes |
| Deploy succeeded, URL returns nothing | No service exposes `path`, or wrong `servicePorts` | references/TROUBLESHOOT.md → Network Issues |
| 502 / 503 from the public URL | Container not listening on the declared port | references/TROUBLESHOOT.md → Network Issues |
| Frontend loads, API calls fail | Browser was handed an internal `.pod` address | See "The two-network rule" below |
| Database never becomes ready | Volume mounted at the data directory root | references/TROUBLESHOOT.md → Database Issues |
| Slow, OOM-killed, or restarting under load | Undersized resources | references/OBSERVE.md → Crash Investigation |
| "Just show me what's happening" | Nothing is broken — observe | references/OBSERVE.md |

## The two-network rule (cause of most "it works locally" bugs)

```
Browser  → service:  <% URL %>/api        ← public route, resolved at deploy time
Service  → service:  api.pod:8000         ← internal DNS, unreachable from a browser
```

Any browser-exposed variable (`NEXT_PUBLIC_*`, `VITE_*`, `REACT_APP_*`) holding a `.pod` address is a bug. Any server-side variable (`DATABASE_URL`, `REDIS_URL`, `OLLAMA_URL`) pointing at `<% URL %>` is also a bug.

## Step 3 — Go deeper only if logs and events were not enough

| Need | Tool |
|------|------|
| Full service definition, restart count, last exit code | `nexlayer_debug_pod_describe` |
| Run a command inside the running container | `nexlayer_debug_shell_open` → `nexlayer_debug_shell_send` → `nexlayer_debug_shell_close` |
| Confirm internal DNS actually resolves | `nexlayer_debug_namespace_dns` |
| Reach one service from inside the network | `nexlayer_debug_proxy_http` |
| Inspect live data / run a read query | `nexlayer_debug_db_query` |
| List or read files in the container | `nexlayer_debug_file_list`, `nexlayer_debug_file_copy_from` |

Close every shell you open (`nexlayer_debug_shell_close`) — orphaned sessions linger.

## Step 4 — Fix, then verify

1. Fix the root cause where it lives: `nexlayer.yaml`, the Dockerfile, or the app code.
2. `nexlayer_validate_yaml` before redeploying.
3. `nexlayer_deploy`, then `nexlayer_check_deployment_status` until healthy.
4. Report the live URL and what actually caused the failure — one sentence, no hedging.

A restart that "fixes" a crash loop without a known cause has not fixed anything. Find the cause.

## Escalation

If the platform itself is misbehaving (validation accepts a config that then fails, or a tool returns an internal error), collect the app name, timestamps, and the tool output, and file it with `nexlayer_submit_issue`. Show the user the draft first.

## Reference Files

| File | Use When |
|------|----------|
| [references/TROUBLESHOOT.md](references/TROUBLESHOOT.md) | Symptom-by-symptom fixes with exact commands |
| [references/OBSERVE.md](references/OBSERVE.md) | Reading status, logs, and events; crash investigation |
