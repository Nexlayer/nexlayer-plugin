# YAML Anti-Patterns for Nexlayer Deployments

> **Purpose:** Prevent deployment failures by avoiding common YAML configuration mistakes
> **Audience:** AI agents generating `nexlayer.yaml` launchfiles
> **Validated:** Against Nexlayer MCP schema and [Liz](https://liz.nexlayer.com/) (Deployment Intelligence Expert)

---

**Key insight from Liz:**
> ".pod DNS is used for internal communication between pods within your application, while `<% URL %>` is designed to dynamically generate URLs that are accessible from outside the pod network, such as through a browser. If you mistakenly use `.pod` DNS in a browser-facing variable like `REACT_APP_API_URL`, this will not work as expected."

---

## Table of Contents

1. [Invalid Application Name](#1-invalid-application-name)
2. [Browser-Facing URL with .pod DNS](#2-browser-facing-url-with-pod-dns)
3. [PostgreSQL Volume Mount to /data](#3-postgresql-volume-mount-to-data)
4. [Missing Image Tag](#4-missing-image-tag)
5. [Missing servicePorts](#5-missing-serviceports)
6. [No Pod with path Field](#6-no-pod-with-path-field)
7. [localhost in Container URLs](#7-localhost-in-container-urls)
8. [Invalid Volume Size Format](#8-invalid-volume-size-format)
9. [REACT_APP_* with .pod DNS](#9-react_app_-with-pod-dns)
10. [Secrets in vars Instead of secrets](#10-secrets-in-vars-instead-of-secrets)
11. [Same mountPath for Multiple Volumes](#11-same-mountpath-for-multiple-volumes)
12. [Invalid Pod Name](#12-invalid-pod-name)
13. [Missing Required Fields](#13-missing-required-fields)
14. [Path Without Leading Slash](#14-path-without-leading-slash)

---

## 1. Invalid Application Name

**Symptom:** Deployment fails with "Invalid application name" validation error

**Why it fails:** Application names must match pattern `^[a-z][a-z0-9.-]{2,63}$`
- Must start with lowercase letter
- Only lowercase alphanumeric, hyphens, and dots allowed
- Minimum 3 characters, maximum 64 characters

**Impact:** Deployment rejected before any resources are created

**❌ Wrong:**
```yaml
application:
  name: My App           # Spaces and uppercase
  name: MyApp            # Uppercase letters
  name: 123-app          # Starts with number
  name: app_name         # Underscores not allowed
  name: ab               # Too short (min 3 chars)
```

**✅ Correct:**
```yaml
application:
  name: my-app           # Lowercase with hyphens
  name: myapp            # All lowercase
  name: my.app.v2        # Dots allowed
  name: app-123          # Numbers allowed (not first)
```

---

## 2. Browser-Facing URL with .pod DNS

**Symptom:** Frontend app can't reach backend API; browser console shows `ERR_NAME_NOT_RESOLVED`

**Why it fails:** `.pod` DNS is internal to Nexlayer's cluster. Browsers run on user machines OUTSIDE the cluster and cannot resolve `.pod` hostnames.

**Impact:** All API calls from browser JavaScript fail silently or with network errors

**❌ Wrong:**
```yaml
# Frontend pod - browser-facing
- name: frontend
  image: my-react-app:latest
  path: /
  servicePorts: [3000]
  vars:
    # Browser will try to call http://api.pod:8000 and FAIL
    API_URL: http://api.pod:8000
    BACKEND_URL: http://backend.pod:3001
```

**✅ Correct:**
```yaml
# Frontend pod - browser-facing
- name: frontend
  image: my-react-app:latest
  path: /
  servicePorts: [3000]
  vars:
    # Browser calls real URL, Nexlayer routes to API pod
    API_URL: <% URL %>/api
    BACKEND_URL: <% URL %>/backend
```

**When to use .pod DNS:**
- Server-to-server communication (Express → PostgreSQL)
- Backend services calling other backends
- Nginx proxy_pass directives
- SSR data fetching (Next.js getServerSideProps)

**When to use <% URL %>:**
- Browser JavaScript fetch() calls
- OAuth redirect URLs
- WebSocket connections from browser
- Any URL the user's browser needs to reach

**When to use <% DOMAIN %>:**
- Same resolution as `<% URL %>` but without the `https://` scheme — just the domain/host (e.g. `app.example.com`)
- Cookie domains (`COOKIE_DOMAIN`), host allowlists, or any setting that expects a bare hostname rather than a full URL

---

## 3. PostgreSQL Volume Mount to /data

**Symptom:** PostgreSQL container fails to start or loses data on restart

**Why it fails:** The platform creates a `lost+found` directory in mounted volumes. PostgreSQL's initdb fails if the data directory is not empty. Mounting to `/var/lib/postgresql/data` without moving PGDATA into a `pgdata` subdirectory triggers this issue, because the data directory then sits at the mount root alongside `lost+found`.

**Impact:** Database container crashes in init loop; data corruption possible

**❌ Wrong:**
```yaml
- name: postgres
  image: postgres:16
  servicePorts: [5432]
  vars:
    POSTGRES_DB: mydb
    PGDATA: /var/lib/postgresql/data       # WRONG: data dir at mount root, lost+found breaks initdb
  volumes:
    - name: pg-data
      size: 10Gi
      mountPath: /var/lib/postgresql/data
```

**✅ Correct:**
```yaml
- name: postgres
  image: postgres:16
  servicePorts: [5432]
  vars:
    POSTGRES_DB: mydb
    PGDATA: /var/lib/postgresql/data/pgdata  # Data dir lives in pgdata subdirectory
  volumes:
    - name: pg-data
      size: 10Gi
      mountPath: /var/lib/postgresql/data    # Volume mounts here; lost+found stays at root
```

---

## 4. Missing Image Tag

**Symptom:** Validation fails with image pattern error; or unpredictable deployments with different versions

**Why it fails:** Image must match pattern requiring explicit tag: `image:tag`

**Impact:** Deployment fails validation; or "latest" tag causes version drift

**❌ Wrong:**
```yaml
pods:
  - name: api
    image: nginx              # No tag
    image: myorg/myapp        # No tag
    image: ghcr.io/org/app    # No tag
```

**✅ Correct:**
```yaml
pods:
  - name: api
    image: nginx:1.25                         # Explicit version
    image: nginx:latest                       # Explicit "latest"
    image: myorg/myapp:v1.2.3                 # Semantic version
    image: ghcr.io/org/app:abc123f            # Git SHA tag
    image: ghcr.io/org/app:2025-01-27         # Date tag
```

---

## 5. Missing servicePorts

**Symptom:** Validation error: "servicePorts is required"

**Why it fails:** Every pod MUST expose at least one port. This is required for health checks and routing.

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
pods:
  - name: worker
    image: my-worker:latest
    # Missing servicePorts - even background workers need a health port
```

**✅ Correct:**
```yaml
pods:
  - name: worker
    image: my-worker:latest
    servicePorts: [8080]      # Health check / metrics port
```

**Note:** Even utility containers, migration pods, and background workers need at least one port for Nexlayer to perform health checks.

---

## 6. No Pod with path Field

**Symptom:** Validation error: "At least one pod must include the 'path' field"

**Why it fails:** Nexlayer needs at least one pod to route external HTTP traffic to. Without a `path`, the deployment has no entry point.

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
pods:
  - name: api
    image: my-api:latest
    servicePorts: [8000]
    # No path - nothing is publicly accessible
  - name: db
    image: postgres:16
    servicePorts: [5432]
```

**✅ Correct:**
```yaml
pods:
  - name: api
    image: my-api:latest
    path: /                   # Public entry point
    servicePorts: [8000]
  - name: db
    image: postgres:16
    servicePorts: [5432]
    # Database doesn't need path - internal only
```

---

## 7. localhost in Container URLs

**Symptom:** Service can't connect to database/cache/other services; connection refused errors

**Why it fails:** Each pod runs in its own container. `localhost` refers to THAT container only, not other pods.

**Impact:** Database connections fail; inter-service communication broken

**❌ Wrong:**
```yaml
pods:
  - name: api
    image: my-api:latest
    servicePorts: [8000]
    vars:
      DATABASE_URL: postgresql://user:pass@localhost:5432/db    # WRONG
      REDIS_URL: redis://localhost:6379                         # WRONG
      CACHE_HOST: 127.0.0.1                                     # WRONG
```

**✅ Correct:**
```yaml
pods:
  - name: api
    image: my-api:latest
    servicePorts: [8000]
    vars:
      DATABASE_URL: postgresql://user:pass@postgres.pod:5432/db  # .pod DNS
      REDIS_URL: redis://redis.pod:6379                          # .pod DNS
      CACHE_HOST: redis.pod                                      # .pod DNS
```

---

## 8. Invalid Volume Size Format

**Symptom:** Validation error on volume size

**Why it fails:** Size must match pattern `^[0-9]+(Mi|Gi)$` - number followed by Mi (mebibytes) or Gi (gibibytes)

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
volumes:
  - name: data
    size: 10GB           # Wrong unit (GB vs Gi)
    size: 10 Gi          # Space not allowed
    size: 10g            # Lowercase not allowed
    size: 10             # Missing unit
    size: "10Gi"         # Quoted (may work, but not recommended)
```

**✅ Correct:**
```yaml
volumes:
  - name: data
    size: 10Gi           # Gibibytes
    size: 512Mi          # Mebibytes
    size: 1Gi            # 1 gibibyte
```

---

## 9. REACT_APP_* with .pod DNS

**Symptom:** React app builds successfully but API calls fail at runtime in browser

**Why it fails:** `REACT_APP_*` environment variables are baked into the JavaScript bundle at BUILD time. When the browser runs this code and tries to call `http://api.pod:8000`, it fails because browsers can't resolve `.pod` DNS.

**Impact:** Frontend appears to work but all API interactions fail

**❌ Wrong:**
```yaml
- name: frontend
  image: my-react-app:latest
  path: /
  servicePorts: [3000]
  vars:
    REACT_APP_API_URL: http://api.pod:8000           # Browser can't resolve
    REACT_APP_BACKEND: http://backend.pod:3001       # Browser can't resolve
```

**✅ Correct (Option A: Use <% URL %>):**
```yaml
- name: frontend
  image: my-react-app:latest
  path: /
  servicePorts: [3000]
  vars:
    REACT_APP_API_URL: <% URL %>/api                 # Browser-resolvable
```

**✅ Correct (Option B: Server-side proxy):**
```yaml
# If your frontend container has nginx/express that proxies to backend,
# use .pod DNS in the PROXY config (server-side), not React vars
- name: frontend
  image: my-react-app-with-proxy:latest
  path: /
  servicePorts: [80]
  vars:
    # These are used by the PROXY SERVER, not browser
    PROXY_API_TARGET: http://api.pod:8000
    # React app calls relative URLs: fetch('/api/...')
```

---

## 10. Secrets in vars Instead of secrets

**Symptom:** Sensitive data exposed in container inspection, logs, or environment dumps

**Why it fails:** `vars` are standard environment variables - visible in `env` output, potentially logged, exposed in crash dumps. `secrets` are mounted as files with restricted permissions.

**Impact:** Security vulnerability; credential exposure

**❌ Wrong:**
```yaml
vars:
  DATABASE_PASSWORD: super-secret-password     # Exposed in env
  API_KEY: sk-1234567890abcdef                 # Exposed in env
  JWT_SECRET: my-jwt-signing-key               # Exposed in env
```

**✅ Correct:**
```yaml
vars:
  DATABASE_URL: postgresql://user:${DB_PASS}@db.pod:5432/mydb  # Reference only

secrets:
  - name: db-password
    data: super-secret-password
    fileName: db.password
    mountPath: /var/secrets
  - name: api-key
    data: sk-1234567890abcdef
    fileName: api.key
    mountPath: /var/secrets
```

**When to use vars:** Non-sensitive configuration (NODE_ENV, LOG_LEVEL, feature flags)
**When to use secrets:** Passwords, API keys, tokens, certificates, private keys

---

## 11. Same mountPath for Multiple Volumes

**Symptom:** Validation error or one volume overwrites another

**Why it fails:** Two volumes cannot mount to the same path - they would conflict

**Impact:** Deployment fails or data loss

**❌ Wrong:**
```yaml
volumes:
  - name: app-data
    size: 10Gi
    mountPath: /data
  - name: cache-data
    size: 5Gi
    mountPath: /data           # CONFLICT: same path as above
```

**✅ Correct:**
```yaml
volumes:
  - name: app-data
    size: 10Gi
    mountPath: /data/app
  - name: cache-data
    size: 5Gi
    mountPath: /data/cache     # Different paths
```

---

## 12. Invalid Pod Name

**Symptom:** Validation error on pod name

**Why it fails:** Pod names must match `^[a-z][a-z0-9-]{1,63}$`
- Must start with lowercase letter
- Only lowercase alphanumeric and hyphens
- Used in `.pod` DNS, so must be valid DNS label

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
pods:
  - name: MyApi              # Uppercase
  - name: my_api             # Underscore
  - name: 1api               # Starts with number
  - name: my.api             # Dots not allowed in pod names
  - name: a                  # Too short (min 2 chars)
```

**✅ Correct:**
```yaml
pods:
  - name: my-api             # Lowercase with hyphens
  - name: api                # Simple
  - name: frontend-v2        # Descriptive
  - name: auth-service       # Service-oriented naming
```

---

## 13. Missing Required Fields

**Symptom:** Validation error listing missing fields

**Why it fails:** Schema requires specific fields at each level

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
application:
  pods:                      # Missing: name
    - image: nginx:latest    # Missing: name, servicePorts
```

**✅ Correct:**
```yaml
application:
  name: my-app               # Required
  pods:
    - name: web              # Required
      image: nginx:latest    # Required
      servicePorts: [80]     # Required
      path: /                # At least one pod needs this
```

**Required fields:**
- `application.name` - Application identifier
- `application.pods` - Array of pods (min 1)
- `pod.name` - Pod identifier
- `pod.image` - Container image with tag
- `pod.servicePorts` - Array of ports (min 1)
- At least one pod must have `path`

---

## 14. Path Without Leading Slash

**Symptom:** Validation error on path field

**Why it fails:** Path must match pattern `^/.*` - must start with forward slash

**Impact:** Deployment rejected

**❌ Wrong:**
```yaml
pods:
  - name: api
    path: api                # Missing leading slash
    path: v1/users           # Missing leading slash
```

**✅ Correct:**
```yaml
pods:
  - name: api
    path: /api               # Correct
    path: /v1/users          # Correct
    path: /                  # Root path
```

---

## Quick Reference: Valid Patterns

| Field | Pattern | Example |
|-------|---------|---------|
| `application.name` | `^[a-z][a-z0-9.-]{2,63}$` | `my-app`, `api.v2` |
| `pod.name` | `^[a-z][a-z0-9-]{1,63}$` | `frontend`, `auth-service` |
| `image` | Must include tag | `nginx:1.25`, `app:latest` |
| `path` | `^/.*` | `/`, `/api`, `/v1` |
| `volume.size` | `^[0-9]+(Mi\|Gi)$` | `10Gi`, `512Mi` |
| `volume.name` | `^[a-z][a-z0-9-]{1,63}$` | `data`, `pg-storage` |

---

## DNS Quick Reference

| Context | Use | Example |
|---------|-----|---------|
| Server → Server | `.pod` DNS | `postgres.pod:5432` |
| Browser → Server | `<% URL %>` | `<% URL %>/api` |
| OAuth callbacks | `<% URL %>` | `<% URL %>/auth/callback` |
| WebSocket from browser | `<% URL %>` | `<% URL %>/ws` |
| Nginx proxy_pass | `.pod` DNS | `http://api.pod:8000` |
| React/Vue env vars | `<% URL %>` | `REACT_APP_API=<% URL %>/api` |
| Bare hostname (no scheme) | `<% DOMAIN %>` | `COOKIE_DOMAIN=<% DOMAIN %>` |
