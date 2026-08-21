# Architecture Anti-Patterns for Nexlayer

> **Purpose:** Guide architectural decisions when deploying to Nexlayer
> **Audience:** AI agents advising on infrastructure and platform choices
> **Validated:** Against Nexlayer MCP schema and [Liz](https://liz.nexlayer.com/) (Deployment Intelligence Expert)

---

**Key insight from Liz:**
> "Terraform is designed for infrastructure provisioning, not application orchestration. Use `nexlayer.yaml` for deploying applications. Evaluate trade-offs between self-hosting and managed services like Supabase, Neon, or Pinecone. Managed services often provide better scalability, reliability, and ease of use."

---

Nexlayer is an **Agent-Native Cloud Platform** that deploys any stack automatically:
- Self-hosted containers (Next.js, FastAPI, Express, Go, Rust, Django)
- External APIs & databases (Supabase, Neon, Pinecone, OpenAI, Stripe)

These anti-patterns help agents make correct architectural recommendations.

---

## Table of Contents

1. [Terraform for Application Deployment](#1-terraform-for-application-deployment)
2. [Docker Compose in Production](#2-docker-compose-in-production)
3. [MonoRepo Without Service Boundaries](#3-monorepo-without-service-boundaries)
4. [Overly Permissive CORS](#4-overly-permissive-cors)
5. [Hardcoded Secrets in Code](#5-hardcoded-secrets-in-code)
6. [Single Point of Failure Database](#6-single-point-of-failure-database)
7. [Synchronous Everything](#7-synchronous-everything)
8. [Fat Containers](#8-fat-containers)
9. [No Health Checks](#9-no-health-checks)
10. [Logging to Stdout Only](#10-logging-to-stdout-only)
11. [Mixing Concerns in Single Container](#11-mixing-concerns-in-single-container)
12. [External Services Without Fallbacks](#12-external-services-without-fallbacks)
13. [Premature Microservices](#13-premature-microservices)
14. [No Graceful Shutdown](#14-no-graceful-shutdown)
15. [Stateful Containers Without Volumes](#15-stateful-containers-without-volumes)

---

## 1. Terraform for Application Deployment

**Symptom:** Agent suggests using Terraform to deploy application containers to Nexlayer

**Why it fails:** Terraform is designed for infrastructure provisioning (VPCs, load balancers, Kubernetes clusters), not application deployment. Nexlayer handles infrastructure automatically - you only define your application.

**Impact:** Unnecessary complexity; fighting the platform instead of using it

**❌ Wrong:**
```hcl
# Terraform - wrong tool for Nexlayer
resource "kubernetes_deployment" "api" {
  metadata {
    name = "my-api"
  }
  spec {
    replicas = 3
    selector {
      match_labels = {
        app = "my-api"
      }
    }
    template {
      spec {
        container {
          image = "my-api:latest"
          port {
            container_port = 8000
          }
        }
      }
    }
  }
}
```

**✅ Correct:**
```yaml
# Nexlayer launchfile - application-focused
application:
  name: my-api
  pods:
    - name: api
      image: my-api:latest
      path: /
      servicePorts: [8000]
```

**When Terraform IS appropriate:**
- Provisioning cloud resources outside Nexlayer
- Managing DNS records at registrar level
- Setting up external managed databases

---

## 2. Docker Compose in Production

**Symptom:** Agent suggests using `docker-compose.yml` for Nexlayer deployment

**Why it fails:** Docker Compose is for local development on a single machine. It lacks:
- Automatic scaling
- Rolling deployments
- Health-based routing
- Persistent storage across restarts
- SSL/TLS termination

**Impact:** No fault tolerance; single machine = single point of failure

**❌ Wrong:**
```yaml
# docker-compose.yml - local dev only
version: '3.8'
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    depends_on:
      - db
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

**✅ Correct:**
```yaml
# nexlayer.yaml - production ready
application:
  name: my-app
  pods:
    - name: api
      image: my-api:latest
      path: /
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://user:pass@db.pod:5432/mydb
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: pgdata
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

**When Docker Compose IS appropriate:**
- Local development and testing
- CI pipelines for integration tests
- Quick prototyping before deployment

---

## 3. MonoRepo Without Service Boundaries

**Symptom:** Agent deploys entire monorepo as single container with all services

**Why it fails:** Monorepos work great for code organization, but deployment should still separate services. One container running frontend, API, and background workers:
- Can't scale independently
- Single failure takes down everything
- Slower deployments (rebuild everything for any change)

**Impact:** Poor resource utilization; cascading failures

**❌ Wrong:**
```yaml
# Single container running everything
application:
  name: my-app
  pods:
    - name: monolith
      image: my-monorepo:latest
      path: /
      servicePorts: [3000, 8000, 5555]  # Frontend, API, worker all in one
      command: "npm run start:all"       # Starts everything
```

**✅ Correct:**
```yaml
# Separate containers from monorepo
application:
  name: my-app
  pods:
    - name: frontend
      image: my-monorepo-frontend:latest  # Built from packages/frontend
      path: /
      servicePorts: [3000]
    - name: api
      image: my-monorepo-api:latest       # Built from packages/api
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://user:pass@db.pod:5432/mydb
    - name: worker
      image: my-monorepo-worker:latest    # Built from packages/worker
      servicePorts: [5555]
```

**When single container IS appropriate:**
- Truly simple apps (static site + API in Next.js)
- Prototypes and MVPs
- Apps with tightly coupled components that always scale together

---

## 4. Overly Permissive CORS

**Symptom:** Agent configures `CORS_ORIGIN: "*"` for all deployments

**Why it fails:** Allowing all origins means any website can make requests to your API. This enables:
- CSRF attacks
- Data exfiltration
- Credential theft via malicious sites

**Impact:** Security vulnerability; API abuse

**❌ Wrong:**
```yaml
vars:
  CORS_ORIGIN: "*"                        # Any website can call your API
  CORS_ALLOW_ALL: "true"                  # No restrictions
  ACCESS_CONTROL_ALLOW_ORIGIN: "*"        # Wide open
```

**✅ Correct:**
```yaml
vars:
  # Restrict to your actual frontend URL
  CORS_ORIGIN: <% URL %>

  # Or for multiple known origins
  CORS_ORIGINS: "https://app.example.com,https://admin.example.com"

  # In your backend code
  # cors({ origin: process.env.CORS_ORIGIN })
```

**When "*" IS appropriate:**
- Public APIs meant for any consumer (like a weather API)
- Development/preview deployments
- Read-only public data endpoints

---

## 5. Hardcoded Secrets in Code

**Symptom:** Agent puts API keys, passwords directly in application code or Dockerfile

**Why it fails:** Secrets in code end up in:
- Git history (forever)
- Container images (inspectable)
- Log outputs
- Error reports

**Impact:** Credential exposure; security breach

**❌ Wrong:**
```dockerfile
# Dockerfile with hardcoded secrets
ENV DATABASE_PASSWORD=super-secret-123
ENV API_KEY=sk-1234567890abcdef
```

```javascript
// Code with hardcoded secrets
const db = new Pool({
  password: 'super-secret-123'  // IN THE CODE
});
```

**✅ Correct:**
```yaml
# nexlayer.yaml with secrets
pods:
  - name: api
    image: my-api:latest
    servicePorts: [8000]
    vars:
      DATABASE_HOST: db.pod
    secrets:
      - name: db-password
        data: ${DB_PASSWORD}           # From environment
        fileName: db.password
        mountPath: /var/secrets
```

```javascript
// Code reads from file or env
const password = fs.readFileSync('/var/secrets/db.password', 'utf8').trim();
// Or from environment variable set by deployment
const password = process.env.DATABASE_PASSWORD;
```

---

## 6. Single Point of Failure Database

**Symptom:** Agent deploys single database instance for production with no backups

**Why it fails:** Single database container means:
- No failover if container crashes
- Data loss if volume corrupts
- Downtime during updates

**Impact:** Data loss; extended downtime

**❌ Wrong:**
```yaml
# Single database, no backup strategy
pods:
  - name: postgres
    image: postgres:16
    servicePorts: [5432]
    vars:
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - name: data
        size: 100Gi
        mountPath: /var/lib/postgresql/data
    # No backup. No replica. Hope nothing goes wrong.
```

**✅ Correct (Option A: Managed Database):**
```yaml
# Use external managed database for production
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    vars:
      # Neon, Supabase, PlanetScale, etc.
      DATABASE_URL: ${NEON_DATABASE_URL}
```

**✅ Correct (Option B: Self-hosted with backup):**
```yaml
pods:
  - name: postgres
    image: postgres:16
    servicePorts: [5432]
    vars:
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - name: data
        size: 100Gi
        mountPath: /var/lib/postgresql/data

  - name: backup
    image: prodrigestivill/postgres-backup-local:16
    servicePorts: [8080]  # Health check
    vars:
      POSTGRES_HOST: postgres.pod
      SCHEDULE: "@daily"
      BACKUP_KEEP_DAYS: 7
    volumes:
      - name: backups
        size: 50Gi
        mountPath: /backups
```

**When single database IS appropriate:**
- Development/staging environments
- Non-critical data (caches, sessions)
- Data that can be reconstructed

---

## 7. Synchronous Everything

**Symptom:** Agent designs all operations as synchronous HTTP request/response

**Why it fails:** Long-running operations block:
- User experience (spinning forever)
- Server resources (connection held open)
- Timeout failures for operations > 30s

**Impact:** Poor UX; timeouts; resource exhaustion

**❌ Wrong:**
```yaml
# API that does everything synchronously
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    # POST /process-video - takes 5 minutes, times out
```

**✅ Correct:**
```yaml
# Async processing with queue
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    vars:
      REDIS_URL: redis://redis.pod:6379
      # POST /process-video returns job ID immediately
      # Client polls GET /jobs/{id} for status

  - name: worker
    image: my-worker:latest
    servicePorts: [8080]
    vars:
      REDIS_URL: redis://redis.pod:6379
      # Processes jobs from queue asynchronously

  - name: redis
    image: redis:alpine
    servicePorts: [6379]
```

**When synchronous IS appropriate:**
- Fast operations (< 5 seconds)
- Simple CRUD operations
- Real-time requirements where async adds too much latency

---

## 8. Fat Containers

**Symptom:** Agent creates container images that are 2GB+ with unnecessary tools

**Why it fails:** Large images cause:
- Slow deployments (download time)
- Wasted disk space
- Larger attack surface
- Slower scaling (new instances take longer to start)

**Impact:** Slow deployments; resource waste

**❌ Wrong:**
```dockerfile
# Fat container with everything
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    nodejs npm python3 python3-pip \
    vim nano curl wget htop \
    build-essential gcc g++ \
    postgresql-client redis-tools \
    # ... 500MB of tools you don't need in production
COPY . /app
```

**✅ Correct:**
```dockerfile
# Minimal production image
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY dist/ ./dist/
USER node
CMD ["node", "dist/index.js"]
# Result: ~150MB instead of 2GB
```

**Dockerfile best practices:**
- Use `-alpine` or `-slim` base images
- Multi-stage builds (build in one stage, copy only artifacts to final)
- Don't install dev dependencies in production
- Remove package manager caches

---

## 9. No Health Checks

**Symptom:** Agent deploys containers without health endpoints

**Why it fails:** Without health checks, Nexlayer can't:
- Know if your app is ready to receive traffic
- Detect when app is unhealthy
- Automatically restart failed containers
- Route traffic away from broken instances

**Impact:** Traffic routed to broken containers; silent failures

**❌ Wrong:**
```yaml
# No health endpoint
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    # App might be running but not accepting requests
    # No way to know if database connection is working
```

**✅ Correct:**
```yaml
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    # Image should expose /health or /healthz endpoint
    # that checks:
    # - Database connectivity
    # - Redis connectivity
    # - External service availability
```

```javascript
// In your application
app.get('/health', async (req, res) => {
  try {
    await db.query('SELECT 1');
    await redis.ping();
    res.json({ status: 'healthy' });
  } catch (error) {
    res.status(503).json({ status: 'unhealthy', error: error.message });
  }
});
```

---

## 10. Logging to Stdout Only

**Symptom:** Agent deploys app that only writes logs to console with no structure

**Why it fails:** Unstructured stdout logs:
- Hard to search and filter
- No correlation between requests
- Lost on container restart
- Can't alert on specific errors

**Impact:** Debugging nightmares; no observability

**❌ Wrong:**
```javascript
// Unstructured logging
console.log('Processing request...');
console.log('Error: ' + error);
console.log('User logged in');
```

**✅ Correct:**
```javascript
// Structured JSON logging
const logger = pino({ level: 'info' });

logger.info({ requestId, userId, action: 'login' }, 'User logged in');
logger.error({ requestId, error: error.message, stack: error.stack }, 'Request failed');
```

```yaml
# Deploy with observability
pods:
  - name: api
    image: my-api:latest
    path: /
    servicePorts: [8000]
    vars:
      LOG_FORMAT: json
      LOG_LEVEL: info
```

**For serious observability, add Langfuse or similar:**
```yaml
# See llm-observability-platform.yaml example
```

---

## 11. Mixing Concerns in Single Container

**Symptom:** Agent runs web server, background workers, and cron jobs in one container

**Why it fails:** Different concerns have different:
- Scaling requirements (more API, same workers)
- Resource needs (CPU vs memory intensive)
- Failure modes (worker crash shouldn't kill API)
- Update cycles

**Impact:** Can't scale independently; cascading failures

**❌ Wrong:**
```dockerfile
# One container does everything
CMD ["sh", "-c", "cron && npm run worker & npm run api"]
```

**✅ Correct:**
```yaml
# Separate containers per concern
pods:
  - name: api
    image: my-app:latest
    path: /
    servicePorts: [8000]
    command: "npm run api"

  - name: worker
    image: my-app:latest
    servicePorts: [8080]
    command: "npm run worker"

  - name: scheduler
    image: my-app:latest
    servicePorts: [8081]
    command: "npm run scheduler"
```

---

## 12. External Services Without Fallbacks

**Symptom:** Agent integrates external APIs without handling failures

**Why it fails:** External services WILL fail:
- Network issues
- Rate limits
- Service outages
- API changes

**Impact:** Your app fails when dependencies fail

**❌ Wrong:**
```javascript
// No error handling, no fallback
const result = await openai.chat.completions.create({...});
return result.choices[0].message;
// If OpenAI is down, your entire app crashes
```

**✅ Correct:**
```javascript
// Circuit breaker pattern with fallback
try {
  const result = await circuitBreaker.fire(() =>
    openai.chat.completions.create({...})
  );
  return result.choices[0].message;
} catch (error) {
  if (error.name === 'CircuitBreakerOpenError') {
    return getFallbackResponse();  // Cached or default response
  }
  throw error;
}
```

```yaml
# Consider self-hosted alternatives
pods:
  - name: ollama
    image: ollama/ollama:latest
    servicePorts: [11434]
    # Local LLM as fallback when OpenAI is down
```

---

## 13. Premature Microservices

**Symptom:** Agent splits simple app into 10+ microservices from day one

**Why it fails:** Microservices add complexity:
- Network latency between services
- Distributed transaction challenges
- More deployment configurations
- Harder debugging across services

**Impact:** Over-engineering; slow development velocity

**❌ Wrong:**
```yaml
# 10 services for a simple TODO app
application:
  name: todo-app
  pods:
    - name: user-service
    - name: auth-service
    - name: todo-service
    - name: notification-service
    - name: email-service
    - name: analytics-service
    - name: search-service
    - name: cache-service
    - name: api-gateway
    - name: frontend
```

**✅ Correct:**
```yaml
# Start simple, split when needed
application:
  name: todo-app
  pods:
    - name: api
      image: todo-api:latest        # Handles users, auth, todos
      path: /api
      servicePorts: [8000]
    - name: frontend
      image: todo-frontend:latest
      path: /
      servicePorts: [3000]
    - name: postgres
      image: postgres:16
      servicePorts: [5432]
```

**When to split into microservices:**
- Different scaling requirements (search needs more resources)
- Different team ownership
- Different deployment cycles
- Service is genuinely independent domain

---

## 14. No Graceful Shutdown

**Symptom:** Agent deploys containers that don't handle SIGTERM

**Why it fails:** During updates/restarts, Nexlayer sends SIGTERM. Without handling:
- In-flight requests are dropped
- Database transactions are interrupted
- Users see errors during deployments

**Impact:** Errors during deployments; data corruption

**❌ Wrong:**
```javascript
// No signal handling
const server = app.listen(8000);
// Container is killed, requests are dropped
```

**✅ Correct:**
```javascript
const server = app.listen(8000);

// Handle shutdown gracefully
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');

  // Stop accepting new requests
  server.close(() => {
    console.log('HTTP server closed');
  });

  // Wait for in-flight requests (max 30s)
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Close database connections
  await db.end();

  process.exit(0);
});
```

---

## 15. Stateful Containers Without Volumes

**Symptom:** Agent deploys database or storage without persistent volumes

**Why it fails:** Container filesystems are ephemeral. When container restarts:
- All data is lost
- Database is empty
- Uploaded files are gone

**Impact:** Data loss on every restart

**❌ Wrong:**
```yaml
pods:
  - name: postgres
    image: postgres:16
    servicePorts: [5432]
    vars:
      POSTGRES_PASSWORD: secret
    # No volumes = data lives in container = data dies with container
```

**✅ Correct:**
```yaml
pods:
  - name: postgres
    image: postgres:16
    servicePorts: [5432]
    vars:
      POSTGRES_PASSWORD: secret
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - name: pgdata
        size: 10Gi
        mountPath: /var/lib/postgresql/data    # Persistent!
```

**Services that NEED volumes:**
- Databases (PostgreSQL, MySQL, MongoDB)
- Search engines (Elasticsearch, Meilisearch)
- Object storage (MinIO)
- Cache with persistence (Redis with AOF)
- Any service storing user data

---

## Decision Framework

### When to Self-Host vs Use Managed Services

| Factor | Self-Host | Managed Service |
|--------|-----------|-----------------|
| Data privacy | Critical | Acceptable |
| Budget | Limited | Available |
| Ops expertise | Available | Limited |
| Compliance | Required | Certified provider OK |
| Latency | Critical | Acceptable |
| Scale | Predictable | Variable/burst |

### Nexlayer Strengths

Use Nexlayer when you need:
- **Any stack deployed**: Containers, databases, vector stores, APIs
- **Automatic wiring**: Services discover each other via `.pod` DNS
- **Zero infrastructure management**: No Kubernetes YAML, no Terraform
- **Instant deployments**: Push and it's live
- **AI agent integration**: MCP for automated deployments

### When to Use External Services

Consider managed services for:
- **Databases**: Neon, Supabase, PlanetScale (automatic backups, scaling)
- **Vector stores**: Pinecone (managed embeddings at scale)
- **Auth**: Clerk, Auth0 (security handled by experts)
- **Payments**: Stripe (PCI compliance)
- **LLMs**: OpenAI, Anthropic (when local models aren't sufficient)

These integrate seamlessly with Nexlayer-deployed applications.
