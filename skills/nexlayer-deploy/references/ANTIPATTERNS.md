# Anti-Patterns Reference

> Common mistakes that cause deployment failures

---

## Critical Anti-Patterns

### 1. localhost in Environment Variables

**The #1 cause of deployment failures**

```yaml
# WRONG - Container can't reach localhost
vars:
  DATABASE_URL: postgresql://user:pass@localhost:5432/db
  REDIS_URL: redis://localhost:6379
  API_URL: http://localhost:8080/api
```

```yaml
# CORRECT - Use internal .pod DNS
vars:
  DATABASE_URL: postgresql://user:pass@postgres.pod:5432/db
  REDIS_URL: redis://redis.pod:6379
  API_URL: http://api.pod:8080/api
```

**Why it fails**: Inside a container, `localhost` means "this container only". Other containers are not on localhost.

---

### 2. Browser Variable with .pod DNS

**Causes "ERR_NAME_NOT_RESOLVED" in browser**

```yaml
# WRONG - Browser can't resolve .pod DNS
vars:
  NEXT_PUBLIC_API_URL: http://api.pod:8080
  REACT_APP_API_URL: http://api.pod:8080
  VITE_API_URL: http://api.pod:8080
```

```yaml
# CORRECT - Browser needs public URL
vars:
  NEXT_PUBLIC_API_URL: <% URL %>/api
  REACT_APP_API_URL: <% URL %>/api
  VITE_API_URL: <% URL %>/api
```

**Why it fails**: Browser code runs on user's machine, which can't resolve internal `.pod` DNS.

---

### 3. PostgreSQL Mount to /data

**Causes "initdb: directory not empty" error**

```yaml
# WRONG - the platform creates lost+found here
volumes:
  - name: pg-data
    size: 10Gi
    mountPath: /var/lib/postgresql/data
```

```yaml
# CORRECT - PostgreSQL creates /data subdirectory
volumes:
  - name: pg-data
    size: 10Gi
    mountPath: /var/lib/postgresql
```

**Why it fails**: the platform creates `lost+found` in mount points. PostgreSQL expects empty directory.

---

### 4. Missing Image Tag

```yaml
# WRONG - Ambiguous, may pull unexpected version
image: nginx
image: postgres
```

```yaml
# CORRECT - Explicit version
image: nginx:latest
image: postgres:16-alpine
```

**Why it fails**: Validation requires explicit tags to prevent "works on my machine" issues.

---

### 5. Missing servicePorts

```yaml
# WRONG - No ports specified
- name: api
  image: my-api:latest
  path: /api
```

```yaml
# CORRECT - Ports required for health checks + routing
- name: api
  image: my-api:latest
  path: /api
  servicePorts: [8080]
```

**Why it fails**: The platform needs to know which port to check and route traffic to.

---

### 6. No Pod Has Path

```yaml
# WRONG - No external entry point
pods:
  - name: api
    image: my-api:latest
    servicePorts: [8080]
    # No path!
  - name: worker
    image: my-worker:latest
    servicePorts: [8001]
```

```yaml
# CORRECT - At least one pod needs path for external access
pods:
  - name: api
    image: my-api:latest
    path: /                   # External entry point
    servicePorts: [8080]
  - name: worker
    image: my-worker:latest
    servicePorts: [8001]      # Internal only is fine
```

**Why it fails**: Without a `path`, no traffic can reach your application.

---

### 7. Invalid Application Name

```yaml
# WRONG - Various invalid names
application:
  name: My App        # Spaces not allowed
  name: MyApp         # Uppercase not allowed
  name: 1-app         # Can't start with number
  name: my_app        # Underscores not allowed
  name: ab            # Too short (min 3)
```

```yaml
# CORRECT - Lowercase, hyphens, starts with letter
application:
  name: my-app
  name: myapp
  name: my-cool-app-v2
```

**Pattern**: `^[a-z][a-z0-9.-]{2,63}$`

---

### 8. Invalid Pod Name

```yaml
# WRONG
pods:
  - name: myAPI       # Uppercase
  - name: my_pod      # Underscore
  - name: My Pod      # Spaces
```

```yaml
# CORRECT
pods:
  - name: api
  - name: my-api
  - name: api-v2
```

**Pattern**: `^[a-z][a-z0-9-]{1,63}$`

---

### 9. Database with Path

```yaml
# WRONG - Database exposed to internet!
- name: postgres
  image: postgres:16-alpine
  path: /db           # Security risk!
  servicePorts: [5432]
```

```yaml
# CORRECT - Database internal only
- name: postgres
  image: postgres:16-alpine
  # No path = internal only
  servicePorts: [5432]
```

**Why it fails**: Databases should never be exposed to the public internet.

---

### 10. Ollama with Path

```yaml
# WRONG - LLM exposed to internet
- name: ollama
  image: ollama/ollama:latest
  path: /ollama       # Anyone can use your LLM!
  servicePorts: [11434]
```

```yaml
# CORRECT - LLM internal only
- name: ollama
  image: ollama/ollama:latest
  # No path = internal only, accessed via api.pod
  servicePorts: [11434]
```

**Why it fails**: Exposing LLMs publicly allows anyone to run expensive inference.

---

### 11. Duplicate Mount Paths

```yaml
# WRONG - Two things can't mount to same path
secrets:
  - name: api-keys
    mountPath: /run/secrets
    data: {...}
  - name: db-creds
    mountPath: /run/secrets   # Conflict!
    data: {...}
```

```yaml
# CORRECT - Unique paths
secrets:
  - name: api-keys
    mountPath: /run/secrets/api
    data: {...}
  - name: db-creds
    mountPath: /run/secrets/db
    data: {...}
```

---

### 12. Sensitive Data in Vars

```yaml
# WRONG - Visible in environment
vars:
  DATABASE_PASSWORD: my-secret-password
  API_KEY: sk-xxxxxxxxxxxx
  JWT_SECRET: super-secret
```

```yaml
# CORRECT - Use secrets for sensitive data
vars:
  NODE_ENV: production
secrets:
  - name: app-secrets
    mountPath: /run/secrets
    data:
      DATABASE_PASSWORD: my-secret-password
      API_KEY: sk-xxxxxxxxxxxx
      JWT_SECRET: super-secret
```

---

### 13. Invalid Volume Size

```yaml
# WRONG - Various invalid formats
volumes:
  - name: data
    size: 10GB        # Wrong unit
  - name: data
    size: 10g         # Wrong unit
  - name: data
    size: 10          # Missing unit
```

```yaml
# CORRECT - Use Mi or Gi
volumes:
  - name: data
    size: 10Gi        # Gibibytes
  - name: cache
    size: 500Mi       # Mebibytes
```

**Pattern**: `^[0-9]+(Mi|Gi)$`

---

### 14. Path Without Leading Slash

```yaml
# WRONG
- name: api
  path: api           # Missing /
```

```yaml
# CORRECT
- name: api
  path: /api          # Leading slash required
```

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Error | Fix |
|--------------|-------|-----|
| localhost in vars | Connection refused | Use `.pod` DNS |
| .pod in browser vars | ERR_NAME_NOT_RESOLVED | Use `<% URL %>` |
| PostgreSQL /data mount | initdb fails | Mount to `/var/lib/postgresql` |
| Missing image tag | Validation error | Add `:tag` |
| Missing servicePorts | No health check | Add `servicePorts: []` |
| No pod with path | No external access | Add `path: /` |
| Uppercase in names | Validation error | Use lowercase |
| Database with path | Security risk | Remove path |
| Duplicate mountPath | Mount conflict | Use unique paths |
| Secrets in vars | Security risk | Use secrets section |
| Invalid size unit | Validation error | Use Mi or Gi |

---

## Detection Patterns

### For Validators to Check

```javascript
// localhost detection
const localhostPatterns = [
  /localhost:\d+/,
  /127\.0\.0\.1/,
  /0\.0\.0\.0:\d+/,
];

// Browser var with .pod
const browserVarPrefixes = ['NEXT_PUBLIC_', 'REACT_APP_', 'VITE_'];
const podDnsPattern = /\.pod(:\d+)?/;

// PostgreSQL mount path
const badPostgresMount = /\/var\/lib\/postgresql\/data$/;

// Missing tag
const missingTag = /^[^:]+$/;  // No colon = no tag

// Invalid names
const validAppName = /^[a-z][a-z0-9.-]{2,63}$/;
const validPodName = /^[a-z][a-z0-9-]{1,63}$/;
```
