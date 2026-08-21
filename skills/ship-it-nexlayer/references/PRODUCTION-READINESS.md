# Production Readiness Guide

> Build durable, horizontally scalable software — not just "works on localhost."

## Mindset: Production Software Engineer

When deploying to Nexlayer, you are shipping to a cloud platform with multiple containers communicating over a network. Code that works locally often fails in production because of hardcoded assumptions. Apply these principles:

1. **No hardcoded URLs or paths** — every endpoint is an environment variable
2. **Stateless by default** — no in-memory session state without a shared backing store
3. **Horizontally scalable** — any container can be replicated without coordination
4. **Fail gracefully** — handle network errors, timeouts, and missing dependencies

## CLAUDE.md for Nexlayer Projects

When deploying a user's project, create or update their `CLAUDE.md` with these conventions:

```markdown
# Nexlayer Deployment Conventions

## Environment Variables (NEVER hardcode)
- All service URLs come from environment variables
- Frontend (browser-facing): use `<% URL %>` in nexlayer.yaml vars
- Backend (server-to-server): use `.pod` DNS (e.g., `db.pod:5432`)
- Bind all servers to `0.0.0.0`, never `localhost` or `127.0.0.1`

## Container Requirements
- Build for `linux/amd64` platform
- Expose a health check endpoint at `/health` or `/healthz`
- Handle SIGTERM for graceful shutdown
- Use multi-stage Docker builds to minimize image size

## Scalability Rules
- No local file storage for user data (use volumes or object storage)
- No in-memory session state (use Redis or database-backed sessions)
- Database connections must use connection pooling with timeouts
- All inter-service communication goes through environment variables
```

## Environment Variables

### NEVER Hardcode URLs

```javascript
// WRONG - breaks in production
const API_URL = "http://localhost:3000/api";
const DB_URL = "postgresql://user:pass@localhost:5432/db";

// RIGHT - works everywhere
const API_URL = process.env.API_URL || "http://localhost:3000/api";
const DB_URL = process.env.DATABASE_URL;
```

### Nexlayer-Specific Variable Patterns

| Variable Context | Use | Example |
|-----------------|-----|---------|
| Server-to-server | `.pod` DNS | `DATABASE_URL: postgresql://user:pass@db.pod:5432/appdb` |
| Browser-facing | `<% URL %>` | `NEXT_PUBLIC_API_URL: <% URL %>/api` |
| OAuth callbacks | `<% URL %>` | `OAUTH_CALLBACK: <% URL %>/auth/callback` |
| Webhooks (Stripe, etc.) | `<% URL %>` | `WEBHOOK_URL: <% URL %>/webhooks/stripe` |

## Bind to 0.0.0.0

Containers MUST listen on all interfaces, not just localhost.

```javascript
// Node.js
app.listen(process.env.PORT || 3000, '0.0.0.0');

// Python (FastAPI/Uvicorn)
// uvicorn main:app --host 0.0.0.0 --port 8000

// Go
http.ListenAndServe(":"+os.Getenv("PORT"), handler)
```

**In Dockerfile:**
```dockerfile
ENV HOST=0.0.0.0
ENV PORT=3000
EXPOSE 3000
```

## Health Check Endpoints

Every service MUST expose a health endpoint. Nexlayer uses it to determine readiness.

```javascript
// Node.js / Express
app.get('/health', (req, res) => {
  res.json({ status: 'ok', uptime: process.uptime() });
});

// With dependency checks
app.get('/health', async (req, res) => {
  try {
    await db.query('SELECT 1');
    res.json({ status: 'ok', db: 'connected' });
  } catch (err) {
    res.status(503).json({ status: 'degraded', db: 'disconnected' });
  }
});
```

```python
# Python / FastAPI
@app.get("/health")
async def health():
    return {"status": "ok"}
```

## CORS Configuration

```javascript
// WRONG - insecure wildcard
app.use(cors({ origin: '*' }));

// RIGHT - restrict to deployment URL
app.use(cors({
  origin: process.env.CORS_ORIGIN || process.env.PUBLIC_URL,
  credentials: true,
}));
```

In nexlayer.yaml:
```yaml
vars:
  CORS_ORIGIN: <% URL %>
```

## Database Connections

### Connection Pooling (Required)

```javascript
// Node.js with pg
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,                    // Pool size
  idleTimeoutMillis: 30000,   // Close idle connections after 30s
  connectionTimeoutMillis: 5000, // Fail fast if can't connect
});
```

```python
# Python with SQLAlchemy
engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_size=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

### PostgreSQL Volume Mount (Critical)

```yaml
# WRONG - data dir at mount root, PostgreSQL init fails
vars:
  PGDATA: /var/lib/postgresql/data
volumes:
  - name: data
    size: 10Gi
    mountPath: /var/lib/postgresql/data

# RIGHT - data dir lives in pgdata subdirectory via PGDATA
vars:
  PGDATA: /var/lib/postgresql/data/pgdata
volumes:
  - name: data
    size: 10Gi
    mountPath: /var/lib/postgresql/data
```

## Graceful Shutdown

Handle SIGTERM to drain connections before container stops.

```javascript
// Node.js
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    pool.end();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000); // Force exit after 10s
});
```

```python
# Python / FastAPI with signal handling
import signal, sys

def shutdown(sig, frame):
    print("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
```

## Secrets vs Vars

| Field | Use For | Example |
|-------|---------|---------|
| `vars` | Non-sensitive config | `NODE_ENV: production` |
| `secrets` | Sensitive credentials | API keys, database passwords, JWT secrets |

```yaml
pods:
  - name: api
    vars:
      NODE_ENV: production
      LOG_LEVEL: info
    secrets:
      - name: api-keys
        data: |
          STRIPE_SECRET_KEY=sk_live_...
          JWT_SECRET=your-secret-here
        mountPath: /run/secrets
```

## Horizontally Scalable Design

### Stateless Services
- No in-memory session storage (use Redis: `redis.pod:6379`)
- No local file uploads (use object storage or volumes)
- No in-process scheduled jobs (use a dedicated worker pod)

### Idempotent Operations
- API endpoints should be safe to retry
- Use database transactions for multi-step operations
- Use unique request IDs for deduplication

### Shared State
```yaml
# Add Redis for shared state
- name: redis
  image: redis:7-alpine
  servicePorts: [6379]
  command: redis-server --appendonly yes
  volumes:
    - name: redis-data
      size: 1Gi
      mountPath: /data
```

Then in your app:
```javascript
// Session store
const RedisStore = require('connect-redis').default;
app.use(session({
  store: new RedisStore({ url: process.env.REDIS_URL }),
  secret: process.env.SESSION_SECRET,
}));
```
