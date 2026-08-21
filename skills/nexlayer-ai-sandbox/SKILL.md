---
name: nexlayer-ai-sandbox
description: Launch a pre-built, production-grade AI application on Nexlayer with no Dockerfile and no YAML — chatbot, code reviewer, code copilot, multi-agent workspace, translation hub, or content moderation. Use when the user wants an AI app running fast rather than deploying their own repo, asks what AI templates or sandboxes are available, or says things like "spin up a chatbot", "deploy the code reviewer", "give me a multi-agent workspace".
license: MIT
compatibility: Requires the Nexlayer MCP server (mcp.nexlayer.ai)
metadata:
  author: nexlayer
  version: "2.1.0"
allowed-tools: Read
---

# Nexlayer AI Sandbox

Nexlayer ships AI applications as one-call deployments. This skill picks the right one and launches it.

## Which skill applies

| The user wants | Skill |
|----------------|-------|
| Their own repo / Dockerfile shipped | `nexlayer-deploy` |
| A pre-built AI app from Nexlayer's catalog | this one |
| To browse what's available | this one |
| A running app fixed | `nexlayer-debug` |

## Flow

1. **Verify auth** — `nexlayer_check_credits`. If it does not return a user, tell the user to sign in to the Nexlayer MCP and stop. Do not attempt a deploy.
2. **List the catalog** — `nexlayerAI_list_sandboxes` returns every sandbox with its description, required inputs, and demo URL. Trust this over any table, including the one below.
3. **Match intent** — pick the closest sandbox. If the request is ambiguous, show the 2–3 nearest matches and ask which one.
4. **Collect inputs** — each sandbox declares the env vars, API keys, and model choices it needs. Ask for anything missing. Never invent a key, a model name, or a default.
5. **Confirm, then launch** — state which sandbox you are deploying and what it will cost in credits, then call the matching `nexlayerAI_deploy_*` tool. These tools deploy immediately when called; never call one speculatively or to "see what it does".
6. **Verify** — `nexlayer_check_deployment_status` until every service is running.
7. **Report the live URL.**

## Catalog

| Tool | What it is |
|------|------------|
| `nexlayerAI_deploy_chatbot` | LLM chatbot with a web UI |
| `nexlayerAI_deploy_code_reviewer` | Security-focused code review agent |
| `nexlayerAI_deploy_code_copilot` | IDE-style coding assistant |
| `nexlayerAI_deploy_multi_agent` | Multi-agent workspace (planner + executor + critic) |
| `nexlayerAI_deploy_translation_hub` | Multi-language translation service |
| `nexlayerAI_deploy_content_guard` | Content moderation and safety classifier |

The catalog changes. `nexlayerAI_list_sandboxes` is the source of truth.

## Boundaries

- Sandboxes are zero-code by design — do not ask the user to write YAML or a Dockerfile. If no sandbox fits, hand off to `nexlayer-deploy`.
- One sandbox per request. Do not fan out across the catalog.
- If a launch fails, switch to `nexlayer-debug` rather than relaunching.

## Reporting

When it is live, keep it under ten lines:

- **Live URL** — always a `*.nexlayer.ai` address; use the URL the platform returns, never a guessed subdomain
- **Sandbox** — which template shipped
- **What it does** — one sentence
- **Try it** — one concrete thing the user can paste into the live app
- **Credits** — consumed, if visible from a `nexlayer_check_credits` delta
