---
name: nexlayer-deploy
description: Deploy containerized apps, APIs, fullstack webapps, AI models, and multi-service systems to Nexlayer and get a live URL. Use when the user asks to ship, deploy, host, publish, or launch something to the cloud, mentions Nexlayer or nexlayer.yaml, or needs a Dockerfile built, pushed, and running in production. Covers the decision tree, service archetypes, networking rules, and production guardrails.
license: MIT
compatibility: Requires the Nexlayer MCP server (mcp.nexlayer.ai) plus docker and git on PATH
metadata:
  author: nexlayer
  version: "2.1.0"
allowed-tools: Bash(docker:*) Bash(git:*) Read Write Edit
---

# Ship It with Nexlayer

## Decision Tree (Start Here)

```
USER REQUEST
    │
    ├─► "Deploy this app" / "Ship to cloud" / "nexlayer"
    │       │
    │       ├─► Has Dockerfile? ──► YES ──► Go to [Deploy Existing]
    │       │                   └─► NO  ──► Go to [Build First]
    │       │
    │       └─► Has nexlayer.yaml? ──► YES ──► Validate & Deploy
    │                              └─► NO  ──► Generate & Deploy
    │
    ├─► "Fix deployment" / "Not working"
    │       └─► Go to [Troubleshoot]
    │
    └─► "What can Nexlayer deploy?"
            └─► ANYTHING with a Dockerfile
```

---

## Glossary

| Term | Definition | Example |
|------|------------|---------|
| **Application** | Root deployment unit containing all pods | `application: { name: my-app, pods: [...] }` |
| **Pod** | A containerized service running your code | `frontend`, `api`, `database` |
| **Launchfile** | `nexlayer.yaml` - defines your entire stack | The YAML file you deploy |
| **Image** | Docker container to run (must include `:tag`) | `nginx:latest`, `postgres:16` |
| **Path** | URL route exposing a pod to the internet | `/`, `/api`, `/admin` |
| **servicePorts** | Ports the container listens on | `[3000]`, `[8080, 8443]` |
| **Vars** | Environment variables (non-sensitive config) | `NODE_ENV: production` |
| **Secrets** | Sensitive data mounted as files | API keys, passwords |
| **Volumes** | Persistent storage surviving restarts | Database files, uploads |
| **`.pod`** | Internal DNS suffix for server-to-server calls | `db.pod:5432` |
| **`<% URL %>`** | Your deployment's public URL (for browsers) | `<% URL %>/api` |
| **`<% REGISTRY %>`** | Nexlayer's container registry prefix | `<% REGISTRY %>/my-app:v1` |
| **Deployment URL** | Live URL after deploy (always `*.nexlayer.ai`) | `https://{env}-{app}.alpha.nexlayer.ai/` |

---

## Ontology (What Things ARE)

> **Ontology first, then topology becomes trivial.**

### Entity Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTITY TYPE    │  WHAT IT IS                │  KEY PROPERTIES              │
├─────────────────────────────────────────────────────────────────────────────┤
│  application    │  Your entire deployment    │  name, url?, pods[]          │
│  pod            │  A containerized service   │  name, image, servicePorts   │
│  volume         │  Persistent disk storage   │  name, size, mountPath       │
│  secret         │  Sensitive data as file    │  name, data, fileName        │
│  registryLogin  │  Private registry auth     │  registry, username, token   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pod Archetypes

| Type | What It IS | Needs `path`? | **EXACT Port** | Communicates Via |
|------|-----------|---------------|----------------|------------------|
| **Frontend** | User-facing UI served to browsers | ✅ Yes (`/`) | 80, 3000 | Receives `<% URL %>` |
| **Backend/API** | Business logic, handles requests | ✅ Yes (`/api`) | 8000, 8080, 3000 | Receives `<% URL %>/api`, calls `.pod` |
| **PostgreSQL** | Relational database | ❌ No | **5432** | `postgresql://user:pass@db.pod:5432/dbname` |
| **MongoDB** | Document database | ❌ No | **27017** | `mongodb://mongo.pod:27017/dbname` |
| **Redis** | Cache / message broker | ❌ No | **6379** | `redis://redis.pod:6379` |
| **Ollama (LLM)** | AI model server | ❌ No | **11434** | `http://ollama.pod:11434` |
| **Qdrant** | Vector database | ❌ No | **6333**, 6334 | `http://qdrant.pod:6333` |
| **Worker** | Background job processor | ❌ No | 8001 (health) | Calls `.pod` services |

**⚠️ Archetype Rules:**
- Database/Cache/LLM/VectorDB pods **NEVER have `path`** (they're internal services)
- If a pod has no `path`, browsers cannot reach it directly (by design)
- Ollama is ALWAYS port `11434`, not `8080`

### Communication Primitives

| Primitive | What It IS | Resolves Where | Use When |
|-----------|-----------|----------------|----------|
| **`{name}.pod`** | Internal DNS hostname | Inside cluster only | Server calls server |
| **`{name}.pod:{port}`** | Internal service endpoint | Inside cluster only | Full connection string |
| **`<% URL %>`** | Deployment's public URL | Replaced at deploy time | Browser needs to call |
| **`<% URL %>/path`** | Public route to specific pod | Via ingress routing | Browser calls API |
| **`<% REGISTRY %>`** | `registry.nexlayer.io/nexlayer-mcp/...` | At deploy time | Private images |

#### ⚠️ CRITICAL: Browser vs Server Variable Rule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VARIABLE PREFIX         │  MUST USE      │  WHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  NEXT_PUBLIC_*           │  <% URL %>     │  Bundled into browser JS        │
│  REACT_APP_*             │  <% URL %>     │  Bundled into browser JS        │
│  VITE_*                  │  <% URL %>     │  Bundled into browser JS        │
│  DATABASE_URL            │  .pod          │  Server-side only               │
│  REDIS_URL               │  .pod          │  Server-side only               │
│  OLLAMA_URL              │  .pod          │  Server-side only               │
│  (no prefix)             │  .pod          │  Assume server unless stated    │
└─────────────────────────────────────────────────────────────────────────────┘

❌ WRONG: NEXT_PUBLIC_API_URL: http://api.pod:8000  (browser can't resolve .pod)
✅ RIGHT: NEXT_PUBLIC_API_URL: <% URL %>/api       (browser can reach public URL)
```

### Relationships

```
application
    │
    ├── name (identifier: becomes namespace)
    ├── url? (if set: permanent deployment)
    ├── registryLogin? (if private images)
    │
    └── pods[] (1 or more services)
            │
            ├── name (identifier: becomes {name}.pod DNS)
            ├── image (what code to run)
            ├── path? (if set: receives external traffic)
            ├── servicePorts[] (how to reach this pod)
            ├── vars{} (config passed as env vars)
            ├── secrets[] (sensitive files)
            ├── volumes[] (persistent storage)
            ├── entrypoint? (override container start)
            └── command? (override container command)
```

### Rules (What MUST Be True)

| Rule | Why |
|------|-----|
| At least one pod must have `path` | Otherwise no external traffic can reach your app |
| Every pod must have `servicePorts` | Health checks and routing require exposed ports |
| Image must include `:tag` | Prevents ambiguous deployments |
| Pod names become DNS: `{name}.pod` | So names must be valid DNS labels |
| Volumes can't share `mountPath` | Filesystem conflict |
| Secrets can't share `mountPath` | Filesystem conflict |

#### ⚠️ PostgreSQL Volume Rule (CRITICAL)

```
❌ WRONG: mountPath: /var/lib/postgresql/data    ← the platform puts lost+found here, breaks initdb
✅ RIGHT: mountPath: /var/lib/postgresql         ← PostgreSQL creates /data subdirectory itself

This is the #1 cause of PostgreSQL startup failures on Nexlayer.
```

#### ⚠️ YAML Generation Checklist

When generating nexlayer.yaml, ALWAYS include:
1. **Connection vars** - Every pod that calls another pod needs a var with `.pod` DNS
2. **Browser vars** - Every `NEXT_PUBLIC_*`, `REACT_APP_*`, `VITE_*` uses `<% URL %>`
3. **Volumes** - PostgreSQL, Ollama, Qdrant, MongoDB all need persistent storage
4. **Correct ports** - Use exact ports from Pod Archetypes table above

---

## Topology (How Things Connect)

> **Once you know what a pod IS, topology is just: `{source}.pod:{port} → {target}.pod:{port}`**

### The Two Networks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                       │
│                                  │                                          │
│                                  │ HTTPS                                    │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         <% URL %>                                    │   │
│  │                    (Your Public Address)                             │   │
│  │         Routes to pods via 'path' field                              │   │
│  └──────────────┬─────────────────────────────┬────────────────────────┘   │
│                 │                             │                             │
│                 ▼                             ▼                             │
│  ┌──────────────────────┐      ┌──────────────────────┐                    │
│  │  path: /             │      │  path: /api          │                    │
│  │  frontend pod        │      │  backend pod         │                    │
│  │  :3000               │      │  :8000               │                    │
│  └──────────────────────┘      └───────────┬──────────┘                    │
│                                            │                                │
│  ══════════════════════════════════════════╪════════════════════════════   │
│           INTERNAL NETWORK (.pod DNS)      │                                │
│  ══════════════════════════════════════════╪════════════════════════════   │
│                                            │                                │
│               ┌────────────────────────────┼────────────────────┐          │
│               │                            │                    │          │
│               ▼                            ▼                    ▼          │
│  ┌──────────────────┐      ┌──────────────────┐    ┌──────────────────┐   │
│  │  db.pod:5432     │      │  redis.pod:6379  │    │  ollama.pod:11434│   │
│  │  PostgreSQL      │      │  Redis           │    │  LLM             │   │
│  └──────────────────┘      └──────────────────┘    └──────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Connection Rules

| From | To | Use | Example |
|------|-----|-----|---------|
| **Browser** | Any pod | `<% URL %>/path` | `fetch('<% URL %>/api/users')` |
| **Server** | Another pod | `{name}.pod:{port}` | `postgres://db.pod:5432/mydb` |
| **NEXT_PUBLIC_*** | API | `<% URL %>` | `NEXT_PUBLIC_API_URL: <% URL %>/api` |
| **REACT_APP_*** | API | `<% URL %>` | `REACT_APP_API: <% URL %>/api` |
| **DATABASE_URL** | Database | `.pod` | `postgresql://u:p@db.pod:5432/app` |
| **REDIS_URL** | Cache | `.pod` | `redis://redis.pod:6379` |
| **OLLAMA_URL** | LLM | `.pod` | `http://ollama.pod:11434` |
| **QDRANT_URL** | VectorDB | `.pod` | `http://qdrant.pod:6333` |
| **OAuth callback** | Your app | `<% URL %>` | `CALLBACK_URL: <% URL %>/auth/cb` |

#### ⚠️ Common Connection Anti-Patterns

```yaml
# ❌ WRONG - Browser can't resolve .pod DNS
vars:
  NEXT_PUBLIC_API_URL: http://api.pod:8000

# ✅ RIGHT - Browser gets public URL at deploy time
vars:
  NEXT_PUBLIC_API_URL: <% URL %>/api
```

```yaml
# ❌ WRONG - Ollama has path (should be internal only)
- name: ollama
  image: ollama/ollama:latest
  path: /llm              # REMOVE THIS
  servicePorts: [8080]    # WRONG PORT

# ✅ RIGHT - Ollama is internal service
- name: ollama
  image: ollama/ollama:latest
  servicePorts: [11434]   # Correct port, no path
```

### Decision Tree

```
"Where does this code run?"
         │
         ├─► Browser (React, Vue, client JS)
         │       │
         │       └─► USE: <% URL %>
         │           WHY: Browser is OUTSIDE cluster, can't resolve .pod
         │
         └─► Server (Node, Python, Go backend)
                 │
                 ├─► Calling another pod?
                 │       └─► USE: {name}.pod:{port}
                 │           WHY: Internal DNS, fast, private
                 │
                 └─► Generating URL for browser?
                         └─► USE: <% URL %>
                         WHY: Browser will use this URL
```

---

## Hard Constraints (Memorize These)

| Field | Pattern | Valid | Invalid |
|-------|---------|-------|---------|
| `application.name` | `^[a-z][a-z0-9.-]{2,63}$` | `my-app`, `api.v2` | `My App`, `123-app` |
| `pod.name` | `^[a-z][a-z0-9-]{1,63}$` | `frontend`, `api` | `myAPI`, `my_pod` |
| `image` | Must have `:tag` | `nginx:latest` | `nginx` |
| `servicePorts` | Required, array | `[80]`, `[3000, 8080]` | omitted |
| `path` | At least one pod | `/`, `/api` | all pods missing path |
| `volume.size` | `^[0-9]+(Mi\|Gi)$` | `10Gi`, `512Mi` | `10GB`, `10` |
| `volume.mountPath` | PostgreSQL special | `/var/lib/postgresql` | `/var/lib/postgresql/data` |

---

## URL Rules (Critical)

```
┌─────────────────────────────────────────────────────────────┐
│  WHERE CODE RUNS          │  USE THIS         │  EXAMPLE   │
├─────────────────────────────────────────────────────────────┤
│  Server → Server          │  .pod DNS         │  api.pod   │
│  Browser → Server         │  <% URL %>        │  <% URL %> │
│  REACT_APP_*, NEXT_PUBLIC_│  <% URL %>        │  <% URL %> │
│  DATABASE_URL, REDIS_URL  │  .pod DNS         │  db.pod    │
│  OAuth callbacks          │  <% URL %>        │  <% URL %> │
└─────────────────────────────────────────────────────────────┘
```

**Rule**: If it runs in a browser, use `<% URL %>`. If it runs on the server, use `.pod`.

---

## Minimal Valid Examples

### 1. Static Site
```yaml
application:
  name: my-site
  pods:
    - name: web
      image: nginx:latest
      path: /
      servicePorts: [80]
```

### 2. API + Database
```yaml
application:
  name: my-api
  pods:
    - name: api
      image: my-api:latest
      path: /
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:pass@db.pod:5432/mydb
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_PASSWORD: pass
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql
```

### 3. Frontend + Backend (Browser Calls API)
```yaml
application:
  name: fullstack
  pods:
    - name: frontend
      image: my-frontend:latest
      path: /
      servicePorts: [3000]
      vars:
        NEXT_PUBLIC_API_URL: <% URL %>/api   # Browser needs real URL
    - name: backend
      image: my-backend:latest
      path: /api
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://u:p@db.pod:5432/app  # Server uses .pod
    - name: db
      image: postgres:16
      servicePorts: [5432]
```

### 4. AI Stack (Ollama + Vector DB)
```yaml
application:
  name: ai-app
  pods:
    - name: app
      image: my-ai-app:latest
      path: /
      servicePorts: [8000]
      vars:
        OLLAMA_URL: http://ollama.pod:11434    # Server-side
        QDRANT_URL: http://qdrant.pod:6333     # Server-side
    - name: ollama
      image: ollama/ollama:latest
      servicePorts: [11434]
    - name: qdrant
      image: qdrant/qdrant:latest
      servicePorts: [6333, 6334]
      volumes:
        - name: storage
          size: 10Gi
          mountPath: /qdrant/storage
```

---

## Deploy Existing (Has Dockerfile)

```bash
# 1. Build for linux/amd64
docker build --platform linux/amd64 -t registry.nexlayer.io/nexlayer-mcp/USERNAME/APP:TAG .

# 2. Push to Nexlayer registry
docker login -u nexlayer-mcp-user -p NexlayerUser01 registry.nexlayer.io
docker push registry.nexlayer.io/nexlayer-mcp/USERNAME/APP:TAG

# 3. Create nexlayer.yaml with pushed image
# 4. Use MCP: nexlayer_validate_yaml then nexlayer_deploy
```

---

## Build First (No Dockerfile)

Generate Dockerfile based on detected stack:

| Detected | Dockerfile |
|----------|------------|
| `package.json` + Next.js | `FROM node:20-alpine` → build → `npm start` |
| `requirements.txt` | `FROM python:3.11-slim` → pip install → `uvicorn` |
| `go.mod` | `FROM golang:1.21-alpine` → build → binary |
| `Cargo.toml` | `FROM rust:1.75` → build → binary |

Then follow [Deploy Existing].

---

## MCP Tools (In Order)

| Step | Tool | When |
|------|------|------|
| 1 | `nexlayer_get_schema` | Get valid YAML structure |
| 2 | `nexlayer_validate_yaml` | Before ANY deploy |
| 3 | `nexlayer_deploy` | After validation passes |
| 4 | `nexlayer_check_deployment_status` | Verify running |
| 5 | `nexlayer_get_deployment_logs` | Debug issues |

### Deployment URL Format

After `nexlayer_deploy` succeeds, your app is live at:

```
https://{env}-{app}.alpha.nexlayer.ai/
```

**Important**: The subdomain format (`{env}-{app}.alpha`) may change, but the domain will **ALWAYS** be `*.nexlayer.ai/`. Never hardcode the full subdomain pattern—rely on the URL returned by Nexlayer or use `nexlayer_check_deployment_status` to get the live URL.

---

## Troubleshoot

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERR_NAME_NOT_RESOLVED` in browser | Used `.pod` in browser-facing var | Change to `<% URL %>` |
| PostgreSQL won't start | Mounted to `/data` | Mount to `/var/lib/postgresql` |
| Image pull failed | Missing tag or wrong registry | Add `:tag`, check image exists |
| 404 on all routes | No pod has `path` | Add `path: /` to entry pod |
| API calls fail from frontend | `REACT_APP_*` uses `.pod` | Use `<% URL %>/api` |
| Validation: invalid name | Uppercase or spaces | Use lowercase, hyphens only |

---

## Beyond a First Deploy

| Need | Where |
|------|-------|
| Managed Postgres/Redis/S3 instead of self-hosting | [references/OPERATIONS.md](references/OPERATIONS.md) |
| Custom domain, DNS, TLS | [references/OPERATIONS.md](references/OPERATIONS.md), [references/DOMAINS.md](references/DOMAINS.md) |
| Private registry credentials | [references/OPERATIONS.md](references/OPERATIONS.md) |
| Moving an app off another host | [references/MIGRATION.md](references/MIGRATION.md) |
| The deploy failed and you need symptom-first fixes | [references/PLAYBOOK.md](references/PLAYBOOK.md) |
| A live deployment broke | the `nexlayer-debug` skill |

---

## Reference Files

Load these on demand — do not read them upfront.

| File | Use When |
|------|----------|
| [schema/nexlayer.schema.json](schema/nexlayer.schema.json) | Machine-readable `nexlayer.yaml` schema (JSON Schema draft-07) |
| [references/ARCHITECTURE.md](references/ARCHITECTURE.md) | Designing topology, ports, volumes, service-to-service calls |
| [references/ANTIPATTERNS.md](references/ANTIPATTERNS.md) | A deploy failed and you need the known-bad patterns |
| [references/DOCKERFILES.md](references/DOCKERFILES.md) | The project has no Dockerfile (24 framework recipes) |
| [references/CONFIGURE.md](references/CONFIGURE.md) | Env vars, secrets, volumes, resource sizing |
| [references/DOMAINS.md](references/DOMAINS.md) | Custom domain, DNS, TLS |
| [references/OPERATIONS.md](references/OPERATIONS.md) | External services, custom domains, private registries |
| [references/MIGRATION.md](references/MIGRATION.md) | Moving an app off another host |
| [references/PLAYBOOK.md](references/PLAYBOOK.md) | The deploy failed — symptom-first fixes |
| [templates/](templates/) | Known-good `nexlayer.yaml` starting points |
| [templates/dockerfiles/](templates/dockerfiles/) | Per-framework Dockerfile starting points |

For failing or unhealthy deployments after a successful deploy, use the `nexlayer-debug` skill.
