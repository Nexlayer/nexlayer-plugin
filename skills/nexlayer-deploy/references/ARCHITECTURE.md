# Architecture Reference

> Deep dive into Nexlayer architecture and networking concepts

---

## Platform Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NEXLAYER CLOUD                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Internet                                                                  │
│      │                                                                      │
│      ▼                                                                      │
│   ┌─────────────────────────────────────────┐                              │
│   │            Load Balancer                │  ← SSL termination           │
│   │         (Ingress Controller)            │  ← Path routing              │
│   └─────────────────────────────────────────┘                              │
│      │                                                                      │
│      ├─── path: /     ───▶  frontend.pod                                   │
│      ├─── path: /api  ───▶  api.pod                                        │
│      └─── path: /ws   ───▶  websocket.pod                                  │
│                                                                             │
│   ┌─────────────────────────────────────────┐                              │
│   │           Internal Network              │  ← .pod DNS                  │
│   │                                         │                               │
│   │   frontend.pod ◄──► api.pod             │                              │
│   │         │              │                │                               │
│   │         └──────┬───────┘                │                               │
│   │                ▼                        │                               │
│   │   postgres.pod    redis.pod             │                              │
│   │                                         │                               │
│   └─────────────────────────────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Two Networks

Nexlayer deployments have two distinct networks:

### 1. External Network (Internet → Pods)

- **Entry**: Load balancer with public IP
- **Routing**: By `path` field in YAML
- **URL**: `<% URL %>` or custom domain
- **SSL**: Automatic (Let's Encrypt)

### 2. Internal Network (Pod → Pod)

- **DNS**: `{pod-name}.pod`
- **Routing**: Direct pod-to-pod
- **Security**: Not exposed to internet
- **URL**: `{pod-name}.pod:{port}`

---

## Path Routing

The `path` field determines external URL routing:

```yaml
pods:
  - name: frontend
    path: /              # <% URL %>/
  - name: api
    path: /api           # <% URL %>/api
  - name: admin
    path: /admin         # <% URL %>/admin
```

**Routing Rules**:
1. Paths are matched by specificity (most specific wins)
2. `/api/v2` matches before `/api`
3. `/` is the catch-all (least specific)
4. Pods without `path` are internal-only

---

## DNS Resolution

### External DNS

```
my-app-abc123.nexlayer.dev  →  Load Balancer IP
app.mycompany.com           →  Load Balancer IP (custom domain)
```

### Internal DNS

```
frontend.pod  →  10.0.0.1  (pod IP)
api.pod       →  10.0.0.2
postgres.pod  →  10.0.0.3
redis.pod     →  10.0.0.4
```

**Pattern**: `{pod-name}.pod` resolves to pod's internal IP

---

## Pod Types

### Frontend Pods

```yaml
- name: frontend
  image: my-frontend:latest
  path: /                    # Has path = external
  servicePorts: [3000]
```

- **External**: Yes (has `path`)
- **Purpose**: Serve web UI to browsers
- **Typical ports**: 80, 3000, 8080

### API/Backend Pods

```yaml
- name: api
  image: my-api:latest
  path: /api                 # Has path = external
  servicePorts: [8080]
  vars:
    DATABASE_URL: postgresql://...@postgres.pod:5432/db
```

- **External**: Yes (has `path`)
- **Purpose**: Handle API requests
- **Connects to**: Databases, caches, other services

### Database Pods

```yaml
- name: postgres
  image: postgres:16-alpine
  # NO path = internal only
  servicePorts: [5432]
```

- **External**: No (no `path`)
- **Purpose**: Data persistence
- **Access**: Only via internal `.pod` DNS

### Worker Pods

```yaml
- name: worker
  image: my-worker:latest
  # NO path = internal only
  servicePorts: [8001]
```

- **External**: No (no `path`)
- **Purpose**: Background jobs, queue processing
- **Access**: Internal APIs, databases

---

## URL Patterns

### Browser Context (Client-Side)

Code running in the user's browser:

```javascript
// React/Next.js/Vue - runs in browser
fetch(`${process.env.NEXT_PUBLIC_API_URL}/users`)
//     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//     Must be public URL: <% URL %>/api
```

**Rule**: Browser code → Use `<% URL %>`

### Server Context (Container)

Code running inside a container:

```javascript
// Node.js API - runs in container
const db = new Pool({
  connectionString: process.env.DATABASE_URL
  //                ^^^^^^^^^^^^^^^^^^^^^^^^^
  //                Internal DNS: postgres.pod:5432
});
```

**Rule**: Server code → Use `.pod` DNS

### The URL Decision Table

| Variable Prefix | Context | URL Pattern |
|-----------------|---------|-------------|
| `NEXT_PUBLIC_*` | Browser | `<% URL %>` |
| `REACT_APP_*` | Browser | `<% URL %>` |
| `VITE_*` | Browser | `<% URL %>` |
| `DATABASE_URL` | Server | `{name}.pod:{port}` |
| `REDIS_URL` | Server | `redis.pod:6379` |
| `*_SERVICE_URL` | Server | `{name}.pod:{port}` |

---

## Service Ports

### What `servicePorts` Does

```yaml
servicePorts: [3000]
```

1. **Health checks**: The platform checks this port is listening
2. **Traffic routing**: Load balancer forwards to this port
3. **Service discovery**: Other pods connect to this port

### Common Ports by Service

| Service | Default Port |
|---------|-------------|
| nginx | 80 |
| Node.js | 3000 |
| Next.js | 3000 |
| Python/FastAPI | 8000 |
| Go | 8080 |
| PostgreSQL | 5432 |
| MySQL | 3306 |
| MongoDB | 27017 |
| Redis | 6379 |
| Ollama | 11434 |
| Qdrant | 6333, 6334 |

### Multiple Ports

```yaml
# Qdrant exposes HTTP and gRPC
servicePorts: [6333, 6334]
```

---

## Volumes Architecture

### How Volumes Work

```
┌──────────────────────────────────────────────────────────────┐
│  Pod: postgres                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Container                                              │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  /var/lib/postgresql  ◄────  Volume: pg-data     │  │  │
│  │  │  (PostgreSQL data)          (10Gi persistent)    │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Volume Lifecycle

1. **Pod created** → Volume provisioned
2. **Pod running** → Volume mounted at `mountPath`
3. **Pod restarted** → Data persists
4. **Pod deleted** → Volume retained (based on policy)

### PostgreSQL Special Case

```yaml
# CORRECT
volumes:
  - name: pg-data
    size: 10Gi
    mountPath: /var/lib/postgresql

# WRONG - the platform creates lost+found which breaks initdb
volumes:
  - name: pg-data
    size: 10Gi
    mountPath: /var/lib/postgresql/data
```

**Why**: the platform creates a `lost+found` directory in mounted volumes. PostgreSQL's `initdb` expects an empty directory and fails if it finds `lost+found`.

---

## Secrets Architecture

### How Secrets Work

```
┌──────────────────────────────────────────────────────────────┐
│  Pod: api                                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Container                                              │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  /run/secrets/api-keys/                          │  │  │
│  │  │  ├── DATABASE_PASSWORD  (file containing secret) │  │  │
│  │  │  ├── JWT_SECRET         (file containing secret) │  │  │
│  │  │  └── API_KEY            (file containing secret) │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Secrets vs Vars

| Aspect | Vars | Secrets |
|--------|------|---------|
| Storage | Environment variable | File on disk |
| Visibility | Process env (ps aux) | File only |
| Use case | Non-sensitive config | Passwords, keys |
| Access | `process.env.VAR` | `fs.readFileSync('/run/secrets/...')` |

---

## Request Flow Example

### User → Frontend → API → Database

```
1. User browser requests: https://my-app.nexlayer.dev/dashboard

2. Load Balancer:
   - Matches path: / → frontend.pod
   - Forwards to frontend:3000

3. Frontend serves HTML:
   - HTML includes: <script>fetch(NEXT_PUBLIC_API_URL + '/users')</script>
   - NEXT_PUBLIC_API_URL = https://my-app.nexlayer.dev/api

4. Browser requests: https://my-app.nexlayer.dev/api/users

5. Load Balancer:
   - Matches path: /api → api.pod
   - Forwards to api:8080

6. API container:
   - Receives request
   - Queries DATABASE_URL = postgresql://...@postgres.pod:5432/db
   - DNS resolves: postgres.pod → 10.0.0.3
   - Connects to postgres container

7. Response flows back:
   - postgres → api → load balancer → browser
```

---

## High Availability

### Pod Replicas (Future)

```yaml
# Coming soon
pods:
  - name: api
    replicas: 3  # Three instances
```

### Current Behavior

- Single replica per pod
- The platform auto-restarts failed pods
- Health checks ensure availability

---

## Resource Limits

### Default Resources

Nexlayer assigns reasonable defaults. Override with:

```yaml
pods:
  - name: api
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "512Mi"
        cpu: "500m"
```

### Resource Guidelines

| Pod Type | Memory Request | Memory Limit |
|----------|---------------|--------------|
| Frontend | 128Mi | 256Mi |
| API | 256Mi | 512Mi |
| PostgreSQL | 256Mi | 1Gi |
| Redis | 64Mi | 128Mi |
| Ollama | 4Gi | 8Gi |

---

## Network Policies (Future)

### Planned Security Features

```yaml
# Coming soon
networkPolicy:
  - from: frontend
    to: api
    ports: [8080]
  - from: api
    to: postgres
    ports: [5432]
```

### Current Behavior

- All pods can communicate within deployment
- External access only through `path` field
- No cross-deployment communication
