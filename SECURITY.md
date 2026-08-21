# Security Policy

## Reporting a vulnerability

Email **support@nexlayer.com** with the details. Please do not open a public issue for anything exploitable.

Include what you can: what you were doing, what happened, and how to reproduce it. We will acknowledge the report and keep you updated while we investigate.

## What lives in this repository

This repo is a distribution package: documentation, YAML examples, and a manifest that points agent clients at Nexlayer's hosted MCP server. It contains **no credentials and no server code**.

| Component | What it does | Runs where |
|-----------|--------------|------------|
| `mcp.json` | Points the client at `https://mcp.nexlayer.ai/api/mcp` over HTTPS | Nothing local; the server is hosted and authenticates each user over OAuth/SSO |
| `skills/`, `commands/`, `agents/`, `rules/` | Markdown instructions for the agent | Nothing executes |
| `hooks/nexlayer-yaml-check.py` | Reads a `nexlayer.yaml` you just edited and prints advisory findings | Locally, when your client fires a file-edit hook |
| `scripts/` | Maintainer tooling — sync, validate, generate | Locally, only when you run it |

The hook script is the only code this plugin runs on your machine. It reads the file you edited, writes findings to stdout, makes no network calls, and always exits 0 — it can report, never block or modify.

## Credentials

The plugin never stores, transports, or logs a credential. Authentication happens between your client and `mcp.nexlayer.ai` over OAuth/SSO, and container-registry auth uses a short-lived per-user token issued by the `nexlayer_build_and_push_image` tool. Every API key, password, and token in the examples under `skills/` is a placeholder (`sk-1234567890abcdef`, `ghp_xxxx`) — none is real, and none should be copied into a real deployment.

Examples show plaintext values in `vars:` so the YAML shape is readable. In a real deployment, put anything sensitive in `secrets:`, not `vars:`.

## Scope

Vulnerabilities in the hosted platform, the MCP server, or the deployment pipeline are not in this repository. Report those to support@nexlayer.com as well, and they will be routed.
