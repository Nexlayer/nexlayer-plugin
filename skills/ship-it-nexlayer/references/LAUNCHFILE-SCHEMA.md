# Nexlayer Deployment Schema Reference

Complete schema reference for `nexlayer.yaml` deployment configurations.

## Schema Overview

```yaml
application:                    # Required - Root configuration
  name: string                  # Required - App identifier
  url: string | null            # Optional - Custom domain
  registryLogin: object         # Optional - Private registry auth
  pods: array                   # Required - Service definitions
```

## Application Object

### `name` (Required)

Globally unique application identifier.

**Constraints:**
- Must start with lowercase letter
- Only lowercase alphanumeric, hyphens, dots allowed
- Length: 3-64 characters
- Pattern: `^[a-z][a-z0-9.-]{2,63}$`

**Examples:**
```yaml
name: my-app
name: ai-service
name: vector-search-api
name: langchain-rag-demo
```

**Invalid:**
```yaml
name: MyApp          # Uppercase not allowed
name: 1-app          # Must start with letter
name: ab             # Too short (min 3 chars)
name: my_app         # Underscores not allowed
```

### `url` (Optional)

Custom domain for production deployments.

**Behavior:**
- **Included**: Creates deployment with your custom domain
- **Omitted**: Creates preview deployment

**Constraints:**
- Valid domain format
- Must be a domain you control
- Pattern: `^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.)+[A-Za-z]{2,6}$`

**Examples:**
```yaml
url: www.myapp.com
url: api.myservice.io
url: demo.example.net
```

### `registryLogin` (Optional)

Authentication for private container registries.

**Required when:** Using private images from authenticated registries.

**Schema:**
```yaml
registryLogin:
  registry: string              # Required - Registry hostname
  username: string              # Required - Registry username
  personalAccessToken: string   # Required - Read-only auth token
```

**Example:**
```yaml
registryLogin:
  registry: ghcr.io
  username: my-org
  personalAccessToken: ghp_1234567890abcdef
```

**Supported registries:**
- `ghcr.io` (GitHub Container Registry)
- `registry.gitlab.com` (GitLab)
- `docker.io` (Docker Hub)
- Any OCI-compliant registry

## Pods Array

List of containerized services. At least one pod required.

**Constraint:** At least one pod must include the `path` field (web-facing).

### Pod Object Schema

```yaml
pods:
  - name: string                # Required
    image: string               # Required
    path: string | null         # Optional (but one pod needs it)
    servicePorts: array         # Required (except resourceType: job)
    vars: object                # Optional
    volumes: array              # Optional
    secrets: array              # Optional
    entrypoint: string          # Optional
    command: string             # Optional
    useGPU: boolean             # Optional
    resourceType: string        # Optional ("deployment" | "statefulset" | "daemonset" | "job")
    replicas: integer           # Optional
    resources: object           # Optional
```

### `name` (Required)

Unique pod identifier within the application.

**Constraints:**
- Must start with lowercase letter
- Only lowercase alphanumeric and hyphens
- Length: 2-64 characters
- Pattern: `^[a-z][a-z0-9-]{1,63}$`

**Purpose:** Used in inter-pod communication URLs (e.g., `http://api.pod:8000`)

**Examples:**
```yaml
name: frontend
name: api
name: database
name: redis
name: vector-db
name: auth-service
```

### `image` (Required)

Docker image to deploy.

**Formats:**

Public images:
```yaml
image: nginx:latest
image: postgres:14
image: node:18-alpine
image: python:3.11-slim
image: redis:7-alpine
```

Private images (with `registryLogin`):
```yaml
image: ghcr.io/my-org/my-app:latest
image: registry.gitlab.com/org/project:v1.2.0
```

**Constraints:**
- Must include tag (`:latest`, `:v1.0`, etc.)
- Use full registry URL (e.g., `ghcr.io/org/image:tag`)
- Registry in image must match `registryLogin.registry`

### `path` (Optional but one required)

URL route for web-facing pods.

**Constraints:**
- Must start with `/`
- Pattern: `^/.*`

**Examples:**
```yaml
path: /           # Root route
path: /api        # API route
path: /admin      # Admin panel
path: /graphql    # GraphQL endpoint
```

**Note:** At least one pod in the application must have a `path` defined.

### `subdomain` (Optional)

DNS label that Nexlayer prepends to the deployment's domain to route traffic to this pod.

**Requires a custom domain:** `application.url` must be set. The subdomain is prepended to your custom domain, so it has no effect on a preview deployment (which gets a random `nexlayer.io` host). Setting `subdomain` without `url` is a validation error.

**Constraints:**
- A single DNS label or a dotted multi-label hostname
- Each label is 1-63 chars, starts/ends with alphanumeric, may contain hyphens
- Pattern: `^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$`

**Examples:**
```yaml
subdomain: api        # api.<deployment-domain>
subdomain: admin      # admin.<deployment-domain>
subdomain: web-v2
subdomain: web.api    # dotted multi-label
```

### `servicePorts` (Required, except for `job`)

List of port numbers exposed by the pod.

**Constraints:**
- At least one port required — unless `resourceType: job`, which runs to completion and exposes no service, so `servicePorts` may be omitted
- Maximum 2768 ports
- Valid range: 1-65535

**Examples:**
```yaml
servicePorts: [80]
servicePorts: [3000]
servicePorts: [8080, 8081]
servicePorts: [5432]
```

### `vars` (Optional)

Environment variables as key-value pairs.

**Use for:**
- Configuration settings
- Inter-pod communication URLs
- Non-sensitive parameters

**Special variables:**
- `<% URL %>` - Resolves to the full deployment URL including scheme (e.g. `https://app.example.com`)
- `<% DOMAIN %>` - Like `<% URL %>` but just the domain/host without the `https://` scheme (e.g. `app.example.com`). Use for cookie domains, host allowlists, or anywhere a bare hostname is needed.
- Pod DNS: `{pod-name}.pod` for server-to-server communication

**Validation Rules:**
- `API_URL` in frontend pods **must** use `<% URL %>` scriptlet (browsers can't resolve `.pod` DNS)

**Examples:**

Frontend pod (browser-facing):
```yaml
vars:
  API_URL: <% URL %>/api      # REQUIRED: Browser needs real URL
  NODE_ENV: production
```

Backend pod (server-to-server):
```yaml
vars:
  DATABASE_URL: postgresql://user:password@db.pod:5432/mydb
  REDIS_URL: redis://redis.pod:6379
  OLLAMA_URL: http://ollama.pod:11434
  CORS_ORIGIN: <% URL %>
```

### `volumes` (Optional)

Persistent storage configurations.

**Schema:**
```yaml
volumes:
  - name: string        # Required - Unique volume name
    size: string        # Required - Storage size
    mountPath: string   # Required - Mount location
```

**Name constraints:**
- Pattern: `^[a-z][a-z0-9-]{1,63}$`

**Size format:**
- Pattern: `^[0-9]+(Mi|Gi)$`
- `Mi` = Mebibytes
- `Gi` = Gibibytes

**MountPath constraints:**
- Must start with `/`
- Must be unique (no conflicts with other volumes or secrets)

**PostgreSQL Warning:**
Mount the volume at `/var/lib/postgresql/data` and set `PGDATA: /var/lib/postgresql/data/pgdata` so the actual data directory lives in the `pgdata` subdirectory. Do NOT leave PGDATA at the mount root (`/var/lib/postgresql/data`), as the `lost+found` directory there prevents initialization.

**Examples:**
```yaml
volumes:
  - name: data
    size: 1Gi
    mountPath: /data

  - name: postgres-data
    size: 10Gi
    mountPath: /var/lib/postgresql/data  # set PGDATA: /var/lib/postgresql/data/pgdata

  - name: uploads
    size: 512Mi
    mountPath: /app/uploads
```

### `secrets` (Optional)

Secure storage for sensitive data files.

**Schema:**
```yaml
secrets:
  - name: string        # Required - Secret identifier
    data: string        # Required - Secret value
    fileName: string    # Required - Filename
    mountPath: string   # Optional - Mount directory
```

**Name constraints:**
- Pattern: `^[a-z][a-z0-9-]{1,63}$`

**Default mountPath:** `/var/secrets/<name>` if not specified

**MountPath constraints:**
- Must start with `/`
- Cannot conflict with volumes or other secrets

**Examples:**
```yaml
secrets:
  - name: api-key
    data: sk-1234567890abcdef
    fileName: api.key
    mountPath: /var/secrets

  - name: db-password
    data: supersecretpassword
    fileName: db.password
    mountPath: /etc/config

  # For JSON/YAML, use base64
  - name: credentials
    data: eyJhcGlfa2V5IjogInNrLTEyMyJ9  # base64 encoded
    fileName: credentials.json
    mountPath: /var/secrets
```

### `useGPU` (Optional)

Enable GPU access for this pod.

**Behavior:**
- When `true`, the pod is scheduled on a GPU-enabled node and the container gains access to available GPUs
- When `false` or omitted, the pod runs on standard CPU-only nodes

**Use for:**
- AI inference workloads (Ollama, vLLM, TGI, etc.)
- Model training or fine-tuning containers
- Any workload that benefits from GPU hardware acceleration

**Example:**
```yaml
- name: ollama
  image: ollama/ollama:latest
  servicePorts: [11434]
  useGPU: true
  volumes:
    - name: ollama-models
      size: 50Gi
      mountPath: /root/.ollama
```

### `entrypoint` (Optional)

Override the default Docker image entrypoint.

**Examples:**
```yaml
entrypoint: /bin/bash
entrypoint: /entrypoint.sh
entrypoint: /usr/local/bin/python
```

### `command` (Optional)

Override the default Docker command.

**Examples:**
```yaml
command: npm start
command: python app.py --port 8000
command: gunicorn -w 4 -b 0.0.0.0:8000 app:app
command: ollama serve
```

### `resourceType` (Optional)

Workload type for this pod. Controls scheduling, identity, and storage semantics.

**Values:**
- `deployment` (default) — Stateless. Replicas are interchangeable. Pods can be rescheduled freely and replicas can scale up/down at any time. Use for web/API tiers, workers, and anything that doesn't write durable local state.
- `statefulset` — Stateful. Each replica gets a stable name (`name-0`, `name-1`, …), a stable network identity, and its own persistent volume that survives rescheduling. Replicas start and stop in order. Use for databases, queues, and any pod that must own durable per-instance storage or be addressable by a fixed name.
- `daemonset` — One pod per node. Exactly one replica runs on every node, and replicas are added or removed as nodes join or leave. Use for node-level agents such as log shippers, metrics collectors, and networking sidecars.
- `job` — Runs to completion. The pod runs its task once and is not restarted on success. Use for batch or one-off work such as database migrations, data seeding, and backups.

**Pick `statefulset` when:**
- The image is a database/queue/store (Postgres, MySQL, Mongo, Redis, RabbitMQ, Kafka, etcd, Elasticsearch, Qdrant, MinIO, Cassandra, ClickHouse, …)
- The pod mounts a volume that must stay paired with the same instance across restarts
- Clients need to reach a specific replica by name (e.g. `db-0.db`)

**Pick `daemonset` when:**
- You need exactly one copy of the pod on every node (log/metrics agents, networking sidecars)
- Coverage should follow the cluster's nodes rather than a fixed replica count

**Pick `job` when:**
- The pod performs a finite task and should exit when done (migrations, seeding, backups)
- You do not want the workload restarted after it succeeds

**Pick `deployment` (or omit) when:**
- The pod is stateless (no on-disk state, or state lives in an external DB/cache)
- Replicas are interchangeable behind a load balancer

**Example:**
```yaml
- name: db
  image: postgres:16
  servicePorts: [5432]
  resourceType: statefulset
  vars:
    PGDATA: /var/lib/postgresql/data/pgdata
  volumes:
    - name: pgdata
      size: 10Gi
      mountPath: /var/lib/postgresql/data

- name: log-agent
  image: fluent-bit:3
  servicePorts: [2020]
  resourceType: daemonset      # one pod per node

- name: migrate
  image: my-app-migrations:v1
  servicePorts: [8080]
  resourceType: job            # runs once to completion

- name: web
  image: my-app:v1
  path: /
  servicePorts: [3000]
  resourceType: deployment   # or omit — this is the default
```

### `replicas` (Optional)

Number of independent instances of this pod to run. Defaults to `1` if omitted.

**Behavior:**
- Each replica shares the same configuration (same image, env, volumes-as-defined, etc.); the platform load-balances traffic across them.
- Use `>1` for horizontal scaling of **stateless** services.

**Constraints:**
- Integer ≥ 1
- Higher counts may be capped by your plan

**When to use `replicas > 1`:**
- Stateless web/API pods (no in-memory session state, sticky-session-free)
- Background workers reading from a shared queue (idempotent jobs)

**When to keep `replicas: 1`:**
- Databases and queues (Postgres, MySQL, Mongo, Redis, RabbitMQ, Kafka, etcd, Elasticsearch, Qdrant, MinIO, …) unless the image is explicitly clustering-aware. Scaling these without configured clustering causes split state and data loss.
- Services that hold per-instance state in memory.
- Single-writer workloads (e.g. cron leaders, schema migrators).

**Example:**
```yaml
- name: web
  image: my-app:v1
  path: /
  servicePorts: [3000]
  replicas: 3
```

### `resources` (Optional)

CPU and memory requests and limits for the pod, in Kubernetes units. Omit to use platform defaults.

**Schema:**
```yaml
resources:
  requests:       # Optional — guaranteed minimum reserved by the scheduler
    cpu: string
    memory: string
  limits:         # Optional — hard cap; CPU is throttled, memory triggers OOMKilled
    cpu: string
    memory: string
```

**CPU units:**
- Whole cores: `1`, `2`, `4`
- Millicores: `100m`, `500m`, `1000m` (1000m = 1 core)
- Pattern: `^([0-9]+m|([0-9]+(\.[0-9]+)?))$`

**Memory units:**
- Binary (IEC): `Ki`, `Mi`, `Gi`, `Ti` — most common in K8s
- Decimal (SI): `K`, `M`, `G`, `T`
- Pattern: `^[0-9]+(\.[0-9]+)?(Ei|Pi|Ti|Gi|Mi|Ki|E|P|T|G|M|K)?$`

**Guidance:**
- Set `requests` to what the app needs at steady state — the scheduler reserves exactly this much.
- Set `limits` to the maximum you're willing to let the pod consume. CPU above the limit gets throttled; memory above the limit triggers an OOMKilled.
- Each `limit` must be ≥ its matching `request` — a limit below its request is rejected at deploy time.

**Example:**
```yaml
- name: web
  image: my-app:v1
  path: /
  servicePorts: [3000]
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
    limits:
      cpu: "2"
      memory: "1Gi"
```

## Complete Examples

### Minimal Web App

```yaml
application:
  name: simple-web
  pods:
    - name: web
      image: nginx:latest
      path: /
      servicePorts: [80]
```

### Fullstack Application

```yaml
application:
  name: fullstack-app
  pods:
    - name: frontend
      image: my-react-app:latest
      path: /
      servicePorts: [3000]
      vars:
        API_URL: http://api.pod:8000

    - name: api
      image: my-api:latest
      path: /api
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://user:password@db.pod:5432/mydb

    - name: db
      image: postgres:14
      servicePorts: [5432]
      vars:
        POSTGRES_USER: user
        POSTGRES_PASSWORD: password
        POSTGRES_DB: mydb
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: postgres-data
          size: 1Gi
          mountPath: /var/lib/postgresql/data
```

### Production with Custom Domain

```yaml
application:
  name: production-app
  url: app.example.com
  pods:
    - name: app
      image: my-app:v2.1.0
      path: /
      servicePorts: [3000]
      vars:
        NODE_ENV: production
        SITE_URL: <% URL %>
```

### Private Registry

```yaml
application:
  name: private-app
  registryLogin:
    registry: ghcr.io
    username: my-org
    personalAccessToken: ghp_xxxxxxxxxxxx
  pods:
    - name: app
      image: ghcr.io/my-org/my-app:latest
      path: /
      servicePorts: [8080]
```
