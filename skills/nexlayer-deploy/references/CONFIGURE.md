---
# ============================================================================
# CONFIGURE SKILL - SPECIFICATION
# ============================================================================
name: nexlayer-configure
version: 2.0.0
description: Advanced YAML configuration for volumes, secrets, private registries

metadata:
  requires:
    mcp_tools:
      - nexlayer_validate_yaml
      - nexlayer_get_schema

  invocation:
    user_invocable: true
    model_invocable: true
    triggers:
      - "add volume"
      - "add secret"
      - "configure"
      - "persistent storage"
      - "environment"
      - "private registry"

contract:
  inputs:
    - existing_yaml          # Current configuration
    - configuration_request  # What to add/change
  outputs:
    - updated_yaml           # Modified configuration
    - explanation            # What was changed and why

# Configuration sections (schema-validated)
sections:
  - volumes
  - secrets
  - registryLogin
  - environment_patterns

---

# Configure Skill

> Advanced YAML configuration for volumes, secrets, and private registries

---

## Quick Reference

| Need | Go To |
|------|-------|
| Persistent storage | [Volumes](#volumes) |
| Sensitive data (passwords, keys) | [Secrets](#secrets) |
| Private registry | [Private Registry Authentication](#private-registry-authentication) |
| Environment patterns | [Environment Variables](#environment-variables) |

---

## Volumes

### When to Use

- Databases (PostgreSQL, MySQL, MongoDB)
- File uploads
- Application data that survives restarts
- Cache that needs persistence

### Basic Configuration

```yaml
volumes:
  - name: data           # Unique identifier
    size: 10Gi           # Size: Mi (megabytes) or Gi (gigabytes)
    mountPath: /data     # Where to mount in container
```

### Database Volume Configurations

#### PostgreSQL (CRITICAL: Correct mount path)

```yaml
- name: postgres
  image: postgres:16-alpine
  servicePorts: [5432]
  volumes:
    - name: pg-data
      size: 10Gi
      mountPath: /var/lib/postgresql  # ✅ CORRECT - NOT /var/lib/postgresql/data
```

#### MySQL

```yaml
- name: mysql
  image: mysql:8
  servicePorts: [3306]
  volumes:
    - name: mysql-data
      size: 10Gi
      mountPath: /var/lib/mysql
```

#### MongoDB

```yaml
- name: mongo
  image: mongo:7
  servicePorts: [27017]
  volumes:
    - name: mongo-data
      size: 10Gi
      mountPath: /data/db
```

### Multiple Volumes

```yaml
volumes:
  - name: data
    size: 10Gi
    mountPath: /app/data
  - name: uploads
    size: 5Gi
    mountPath: /app/uploads
  - name: cache
    size: 1Gi
    mountPath: /app/cache
```

**Rule**: Each volume needs a unique `mountPath`.

---

## Secrets

### When to Use Secrets vs Vars

| Use Secrets For | Use Vars For |
|-----------------|--------------|
| API keys | NODE_ENV |
| Database passwords | LOG_LEVEL |
| JWT secrets | PORT |
| OAuth credentials | Feature flags |
| TLS certificates | Non-sensitive config |

### Basic Configuration

```yaml
secrets:
  - name: db-password           # Unique secret name
    data: "mypassword"          # Secret value (string)
    fileName: "DB_PASSWORD"     # Filename created at mountPath
    mountPath: /var/secrets     # Optional (default: /var/secrets/<name>)
```

**Schema requires**: `name`, `data`, `fileName` (mountPath is optional)

### Reading Secrets in Code

Secrets are mounted as **files**, not environment variables:

**Node.js**:
```javascript
const fs = require('fs');
const dbPassword = fs.readFileSync('/var/secrets/DB_PASSWORD', 'utf8').trim();
```

**Python**:
```python
with open('/var/secrets/DB_PASSWORD') as f:
    db_password = f.read().strip()
```

**Go**:
```go
password, _ := os.ReadFile("/var/secrets/DB_PASSWORD")
```

### Multiple Secrets

```yaml
secrets:
  - name: db-password
    data: "postgres-secret-123"
    fileName: "DB_PASSWORD"
    mountPath: /var/secrets

  - name: jwt-secret
    data: "jwt-signing-key-xyz"
    fileName: "JWT_SECRET"
    mountPath: /var/secrets

  - name: stripe-key
    data: "sk_live_xxx"
    fileName: "STRIPE_KEY"
    mountPath: /var/secrets/api
```

**Rule**: Each secret needs a unique `name`. Use different `mountPath` to organize.

---

## Private Registry Authentication

### When Needed

- Private Docker Hub images
- GitHub Container Registry (ghcr.io)
- GitLab Container Registry
- Any private registry

### Configuration

```yaml
application:
  name: my-app
  registryLogin:
    registry: ghcr.io
    username: your-username
    personalAccessToken: ghp_your_token   # Read-only token
  pods:
    - name: api
      image: ghcr.io/your-org/your-app:latest
      # ...
```

**Schema requires**: `registry`, `username`, `personalAccessToken`

### Registry Examples

**GitHub Container Registry**:
```yaml
registryLogin:
  registry: ghcr.io
  username: your-github-username
  personalAccessToken: ghp_xxxxxxxxxxxx
```

**GitLab Container Registry**:
```yaml
registryLogin:
  registry: registry.gitlab.com
  username: your-gitlab-username
  personalAccessToken: glpat-xxxxxxxxxxxx
```

**Docker Hub (private)**:
```yaml
registryLogin:
  registry: docker.io
  username: your-username
  personalAccessToken: dckr_pat_xxxx
```

---

## Environment Variables

### Patterns

#### Browser Variables (client-side)

```yaml
vars:
  # Next.js
  NEXT_PUBLIC_API_URL: <% URL %>/api
  NEXT_PUBLIC_APP_NAME: "My App"

  # Create React App
  REACT_APP_API_URL: <% URL %>/api

  # Vite
  VITE_API_URL: <% URL %>/api
```

**Rule**: All browser variables MUST use `<% URL %>` for URLs.

#### Server Variables (backend)

```yaml
vars:
  # Environment
  NODE_ENV: production
  LOG_LEVEL: info

  # Database (use .pod DNS)
  DATABASE_URL: postgresql://postgres:postgres@postgres.pod:5432/app

  # Redis (use .pod DNS)
  REDIS_URL: redis://redis.pod:6379

  # Internal services (use .pod DNS)
  USER_SERVICE_URL: http://users.pod:8080
  OLLAMA_URL: http://ollama.pod:11434
```

**Rule**: All server-to-server URLs MUST use `.pod` DNS.

#### CORS Configuration

```yaml
vars:
  CORS_ORIGIN: <% URL %>
  # Or multiple origins:
  CORS_ORIGINS: "<% URL %>,https://other-domain.com"
```

---

## Complete Example

```yaml
application:
  name: production-app
  url: app.example.com                    # Custom domain (omit for 2-hour preview)
  registryLogin:                          # Only if using private registry
    registry: ghcr.io
    username: myorg
    personalAccessToken: ghp_xxx

  pods:
    - name: frontend
      image: ghcr.io/myorg/frontend:v1.0.0
      path: /
      servicePorts: [3000]
      vars:
        NEXT_PUBLIC_API_URL: <% URL %>/api

    - name: api
      image: ghcr.io/myorg/api:v1.0.0
      path: /api
      servicePorts: [8080]
      vars:
        NODE_ENV: production
        DATABASE_URL: postgresql://app:secure-password@postgres.pod:5432/app
        REDIS_URL: redis://redis.pod:6379
      secrets:
        - name: db-password
          data: "secure-password"
          fileName: "DB_PASSWORD"
          mountPath: /var/secrets
        - name: jwt-secret
          data: "jwt-signing-key"
          fileName: "JWT_SECRET"
          mountPath: /var/secrets

    - name: postgres
      image: postgres:16-alpine
      servicePorts: [5432]
      vars:
        POSTGRES_USER: app
        POSTGRES_PASSWORD: secure-password
        POSTGRES_DB: app
      volumes:
        - name: pg-data
          size: 20Gi
          mountPath: /var/lib/postgresql

    - name: redis
      image: redis:7-alpine
      servicePorts: [6379]
```
