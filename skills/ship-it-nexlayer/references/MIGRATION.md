# Migration Guide: Deploy to Nexlayer

> Migrate your fullstack apps from any platform to Nexlayer with complete control.

---

## Quick Reference

| Platform | Export Method | Database Export | Difficulty |
|----------|--------------|-----------------|------------|
| [Vercel](#from-vercel) | Git repo (you already have it) | External DB or N/A | Easy |
| [Railway](#from-railway) | Git repo + `pg_dump` | `pg_dump` from TCP proxy | Medium |
| [Render](#from-render) | Git repo + `pg_dump` | `pg_dump` from external URL | Medium |
| [Fly.io](#from-flyio) | Git repo + `fly.toml` conversion | `pg_dump` via `fly postgres` | Medium |
| [DigitalOcean](#from-digitalocean) | Git repo + `pg_dump` | `pg_dump` from managed DB | Medium |
| [Lovable](#from-lovable) | GitHub sync (built-in) | Supabase export | Easy |
| [Replit](#from-replit) | GitHub sync or ZIP export | Manual export | Medium |
| [Base44](#from-base44) | ZIP export (paid plans only) | Cannot export backend | Hard |

---

## Universal Migration Steps

Every migration follows this pattern:

```
1. EXPORT CODE     → Get your code to a Git repository
2. EXPORT DATABASE → pg_dump your PostgreSQL data
3. BUILD IMAGE     → Create Dockerfile if missing
4. PUSH IMAGE      → Push to registry.nexlayer.io
5. CREATE YAML     → Generate nexlayer.yaml
6. DEPLOY          → nexlayer_deploy
7. IMPORT DATA     → pg_restore into new database
8. UPDATE SECRETS  → Stripe webhooks, OAuth callbacks, etc.
```

---

## From Vercel

### What Vercel Apps Look Like
- Next.js, React, or static sites
- Serverless API routes (`/api/*`)
- Often uses external databases (Supabase, PlanetScale, Neon)
- Environment variables in Vercel dashboard

### Migration Steps

**1. You Already Have Your Code**
```bash
# Your repo is already on GitHub/GitLab
git clone https://github.com/you/your-app
cd your-app
```

**2. Configure Next.js for Standalone Mode**
```javascript
// next.config.js
module.exports = {
  output: 'standalone',
}
```

**3. Create Dockerfile**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

**4. Build and Push**

Call `nexlayer_build_and_push_image imageName=your-app tag=v1` — it returns the exact target ref (`registry.nexlayer.io/<your JWT sub>/your-app:v1`) and the login/push commands using your per-user JWT.

```bash
# Export the JWT the tool returns:
export NEXLAYER_JWT="…"

docker build --platform linux/amd64 -t registry.nexlayer.io/YOUR_USER_ID/your-app:v1 .
echo "$NEXLAYER_JWT" | docker login registry.nexlayer.io -u oauth2accesstoken --password-stdin
docker push registry.nexlayer.io/YOUR_USER_ID/your-app:v1
```

**5. Create nexlayer.yaml**
```yaml
application:
  name: your-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/your-app:v1
      path: /
      servicePorts: [3000]
      vars:
        NODE_ENV: production
        # Copy from Vercel dashboard → Settings → Environment Variables
        DATABASE_URL: ${DATABASE_URL}
        NEXT_PUBLIC_SUPABASE_URL: ${SUPABASE_URL}
        STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
```

### Vercel-Specific Considerations

| Vercel Feature | Nexlayer Equivalent |
|----------------|---------------------|
| Serverless Functions | Runs as Node.js server (all routes work) |
| Edge Functions | Not supported (use standard middleware) |
| Image Optimization | Works via `sharp` library |
| Environment Variables | `vars` in nexlayer.yaml |
| Vercel Postgres | Migrate to self-hosted PostgreSQL pod |
| Vercel KV | Add Redis pod |

### If Using Vercel Postgres
```yaml
application:
  name: your-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/your-app:v1
      path: /
      servicePorts: [3000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

---

## From Railway

### What Railway Apps Look Like
- Any language (auto-detected or Dockerfile)
- Managed PostgreSQL, Redis, MongoDB
- Environment variables via dashboard or `railway.json`
- Private networking between services

### Migration Steps

**1. Get Your Code**
```bash
# Already connected to GitHub
git clone https://github.com/you/your-app
```

**2. Export Database**
```bash
# Get connection string from Railway dashboard → PostgreSQL → Connect
# Use the PUBLIC URL (not private) for external access

pg_dump "postgresql://postgres:PASSWORD@HOST:PORT/railway" \
  --format=custom \
  --no-owner \
  --no-acl \
  > railway_backup.dump
```

**3. Map Railway Config to Nexlayer**

| Railway | Nexlayer |
|---------|----------|
| `DATABASE_URL` (private) | `postgresql://user:pass@db.pod:5432/app` |
| `DATABASE_PUBLIC_URL` | Not needed (use `.pod` DNS) |
| `REDIS_URL` (private) | `redis://redis.pod:6379` |
| Port (auto-detected) | Explicit in `servicePorts` |

**4. Create nexlayer.yaml**
```yaml
application:
  name: your-railway-app
  pods:
    - name: api
      image: registry.nexlayer.io/YOUR_USER_ID/api:v1
      path: /
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
        REDIS_URL: redis://redis.pod:6379
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
    - name: redis
      image: redis:7-alpine
      servicePorts: [6379]
```

**5. Deploy and Import Data**
```bash
# Deploy first
nexlayer_deploy(yamlContent)

# Then import data via psql (after deployment)
# Get the public DATABASE_URL from deployment status
pg_restore --verbose --clean --no-owner \
  -d "postgresql://postgres:password@YOUR_NEXLAYER_DB_URL:5432/app" \
  railway_backup.dump
```

---

## From Render

### What Render Apps Look Like
- Web services, background workers, cron jobs
- Managed PostgreSQL
- Environment groups (shared variables)
- `render.yaml` for Infrastructure as Code

### Migration Steps

**1. Get Your Code**
```bash
git clone https://github.com/you/your-app
```

**2. Export Database**
```bash
# Get external connection string from Render Dashboard
# PostgreSQL → Info → External Database URL

pg_dump "postgres://USER:PASS@HOST:5432/DBNAME" \
  --format=custom \
  --no-owner \
  --no-acl \
  > render_backup.dump
```

**3. Convert render.yaml to nexlayer.yaml**

**Render render.yaml:**
```yaml
services:
  - type: web
    name: api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port 8000
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: mydb
          property: connectionString
databases:
  - name: mydb
    plan: starter
```

**Nexlayer nexlayer.yaml:**
```yaml
application:
  name: your-render-app
  pods:
    - name: api
      image: registry.nexlayer.io/YOUR_USER_ID/api:v1
      path: /
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

### Render Environment Groups → Nexlayer Vars
Copy all variables from Render Dashboard → Environment → Environment Groups into your nexlayer.yaml `vars` section.

---

## From Fly.io

### What Fly.io Apps Look Like
- Uses `fly.toml` configuration
- Runs Docker containers as micro-VMs
- Managed Postgres via `fly postgres`
- Global deployment with `fly regions`

### Migration Steps

**1. Get Your Code**
```bash
git clone https://github.com/you/your-app
```

**2. Export Database**
```bash
# Connect to Fly Postgres
fly postgres connect -a your-db-app

# From another terminal, use proxy
fly proxy 5432 -a your-db-app

# Then dump
pg_dump "postgresql://postgres:PASSWORD@localhost:5432/your_db" \
  --format=custom \
  --no-owner \
  > fly_backup.dump
```

**3. Convert fly.toml to nexlayer.yaml**

**Fly fly.toml:**
```toml
app = "my-app"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true

[[services]]
  internal_port = 8080
  protocol = "tcp"
```

**Nexlayer nexlayer.yaml:**
```yaml
application:
  name: my-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/my-app:v1
      path: /
      servicePorts: [8080]
      vars:
        PORT: "8080"
```

### Fly Secrets → Nexlayer Secrets
```bash
# List Fly secrets
fly secrets list -a your-app

# Recreate in nexlayer.yaml
secrets:
  - name: api-key
    data: ${YOUR_SECRET}
    fileName: api.key
    mountPath: /var/secrets
```

---

## From DigitalOcean

### What DO App Platform Apps Look Like
- Auto-detected from GitHub
- Managed databases
- `.do/app.yaml` or dashboard config

### Migration Steps

**1. Get Your Code**
```bash
git clone https://github.com/you/your-app
```

**2. Export Database**
```bash
# Get connection string from DO Dashboard
# Databases → Your DB → Connection Details → Connection String

pg_dump "postgresql://USER:PASS@HOST:25060/defaultdb?sslmode=require" \
  --format=custom \
  --no-owner \
  > do_backup.dump
```

**3. Convert .do/app.yaml to nexlayer.yaml**

**DigitalOcean .do/app.yaml:**
```yaml
name: my-app
services:
  - name: web
    github:
      repo: you/your-app
      branch: main
    run_command: npm start
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${db.DATABASE_URL}
databases:
  - name: db
    engine: PG
    production: true
```

**Nexlayer nexlayer.yaml:**
```yaml
application:
  name: my-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/my-app:v1
      path: /
      servicePorts: [3000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

---

## From Lovable

### What Lovable Apps Look Like
- AI-generated fullstack apps
- React/Next.js frontend
- Often connected to Supabase
- GitHub sync available

### Migration Steps

**1. Export to GitHub**
```
Settings → Connectors → GitHub → Connect project
```
Your code syncs automatically to your GitHub repository.

**2. Clone and Add Dockerfile**
```bash
git clone https://github.com/you/lovable-app
cd lovable-app
```

**3. Create Dockerfile** (Lovable apps are typically Vite/React)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**4. Create nexlayer.yaml**
```yaml
application:
  name: lovable-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/lovable-app:v1
      path: /
      servicePorts: [80]
      vars:
        # Copy from Lovable's environment settings
        VITE_SUPABASE_URL: ${SUPABASE_URL}
        VITE_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
```

### Lovable + Supabase → Nexlayer + Self-Hosted PostgreSQL

If you want to migrate away from Supabase:

```yaml
application:
  name: lovable-app
  pods:
    - name: web
      image: registry.nexlayer.io/YOUR_USER_ID/lovable-app:v1
      path: /
      servicePorts: [80]
      vars:
        VITE_API_URL: <% URL %>/api
    - name: api
      image: registry.nexlayer.io/YOUR_USER_ID/lovable-api:v1
      path: /api
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

---

## From Replit

### What Replit Apps Look Like
- Various languages (Python, Node.js, etc.)
- Uses `.replit` and `replit.nix` for configuration
- GitHub integration available
- Built-in database (key-value store)

### Migration Steps

**1. Export to GitHub**
```
Version Control tab → Create a Git repo → Connect to GitHub
```

Or use the **replit-lifeboat** exporter:
```bash
# https://github.com/hackclub/replit-lifeboat
```

**2. Clone and Clean Up**
```bash
git clone https://github.com/you/replit-app
cd replit-app

# Remove Replit-specific files
rm -rf .replit replit.nix .upm
```

**3. Create Dockerfile**

For Python:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

For Node.js:
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]
```

**4. Migrate Replit Database**

Replit's database is a simple key-value store. Export manually:
```python
# export_db.py (run in Replit before migration)
from replit import db
import json

data = {key: db[key] for key in db.keys()}
with open('replit_db_export.json', 'w') as f:
    json.dump(data, f)
```

Then import into PostgreSQL or Redis on Nexlayer.

**5. Create nexlayer.yaml**
```yaml
application:
  name: replit-app
  pods:
    - name: api
      image: registry.nexlayer.io/YOUR_USER_ID/replit-app:v1
      path: /
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

---

## From Base44

### Important Limitation

**Base44 has vendor lock-in**: The backend code is hidden inside `base44-sdk` and runs on Base44's servers. You can only export frontend code on paid plans ($50+/month).

### What You Can Migrate

| Exportable | Not Exportable |
|------------|----------------|
| Frontend React code | Backend logic |
| Custom functions you wrote | Database schema/data |
| Static assets | Authentication logic |

### Migration Steps (Partial)

**1. Export ZIP (Paid Plans Only)**
```
More actions (•••) → Export project as ZIP
```

**2. Analyze What You Have**
The exported code will be React frontend. You'll need to:
- Recreate the backend from scratch
- Design your own database schema
- Implement authentication

**3. Create New Backend**

If Base44 was calling APIs, recreate them:
```python
# main.py (new FastAPI backend)
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/items")
def get_items():
    # Recreate your Base44 backend logic
    return {"items": []}
```

**4. Create nexlayer.yaml**
```yaml
application:
  name: base44-migration
  pods:
    - name: frontend
      image: registry.nexlayer.io/YOUR_USER_ID/frontend:v1
      path: /
      servicePorts: [80]
      vars:
        VITE_API_URL: <% URL %>/api
    - name: api
      image: registry.nexlayer.io/YOUR_USER_ID/api:v1
      path: /api
      servicePorts: [8000]
      vars:
        DATABASE_URL: postgresql://postgres:password@db.pod:5432/app
    - name: db
      image: postgres:16
      servicePorts: [5432]
      vars:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
        POSTGRES_DB: app
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - name: data
          size: 10Gi
          mountPath: /var/lib/postgresql/data
```

### Recommendation

If you're on Base44 and considering migration, the sooner you move, the less backend logic you'll need to recreate. Consider Lovable or Replit instead, which offer better export options.

---

## Database Migration Deep Dive

### PostgreSQL: pg_dump and pg_restore

**Export (from source platform):**
```bash
# Custom format (recommended - allows parallel restore)
pg_dump "$SOURCE_DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --verbose \
  > backup.dump

# Plain SQL (human-readable, larger file)
pg_dump "$SOURCE_DATABASE_URL" \
  --no-owner \
  --no-acl \
  > backup.sql
```

**Import (to Nexlayer PostgreSQL pod):**
```bash
# First, deploy your app with empty database
nexlayer_deploy(yamlContent)

# Get the database connection (after pod is running)
# Use nexlayer_check_deployment_status to get the URL

# Restore custom format
pg_restore \
  --verbose \
  --clean \
  --no-owner \
  --no-acl \
  -d "$NEXLAYER_DATABASE_URL" \
  backup.dump

# Or restore plain SQL
psql "$NEXLAYER_DATABASE_URL" < backup.sql
```

### Version Compatibility

| Source Version | Target Version | Notes |
|----------------|----------------|-------|
| PostgreSQL 14 | PostgreSQL 16 | Works (upgrade) |
| PostgreSQL 16 | PostgreSQL 14 | May fail (downgrade) |
| PostgreSQL 15 | PostgreSQL 15 | Best compatibility |

**Rule**: Use the same major version or upgrade. Never downgrade.

### Large Database Tips

```bash
# Parallel dump (faster for large DBs)
pg_dump "$SOURCE" --jobs=4 --format=directory --file=backup_dir

# Parallel restore
pg_restore --jobs=4 -d "$TARGET" backup_dir

# Compress during transfer
pg_dump "$SOURCE" | gzip > backup.sql.gz
gunzip -c backup.sql.gz | psql "$TARGET"
```

---

## Stripe Migration

### Update Webhook Endpoints

**Before (old platform):**
```
https://your-app.vercel.app/api/webhooks/stripe
```

**After (Nexlayer):**
```
<% URL %>/api/webhooks/stripe
```

### Steps

1. **Get your new Nexlayer URL** after deployment
2. **Stripe Dashboard** → Developers → Webhooks
3. **Add endpoint** with new URL
4. **Copy new webhook signing secret**
5. **Update nexlayer.yaml:**
```yaml
vars:
  STRIPE_WEBHOOK_SECRET: ${NEW_WEBHOOK_SECRET}
```

### Environment Variable Mapping

```yaml
vars:
  # Stripe (same keys, new webhook secret)
  STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
  STRIPE_PUBLISHABLE_KEY: ${STRIPE_PUBLISHABLE_KEY}
  STRIPE_WEBHOOK_SECRET: ${NEW_WEBHOOK_SECRET}  # ← New!

  # URLs that Stripe needs
  STRIPE_SUCCESS_URL: <% URL %>/success
  STRIPE_CANCEL_URL: <% URL %>/cancel
```

### Test Mode vs Live Mode

| Environment | Stripe Mode | API Keys |
|-------------|-------------|----------|
| Development | Test | `sk_test_...` |
| Staging | Test (separate account recommended) | `sk_test_...` |
| Production | Live | `sk_live_...` |

---

## OAuth Migration

### Update Callback URLs

For each OAuth provider (Google, GitHub, etc.):

1. **Go to provider's developer console**
2. **Update authorized redirect URIs:**
   - Remove: `https://your-app.vercel.app/auth/callback`
   - Add: Your Nexlayer URL + `/auth/callback`

### nexlayer.yaml for OAuth

```yaml
vars:
  # OAuth callbacks use <% URL %> (browser-facing)
  NEXTAUTH_URL: <% URL %>
  GOOGLE_CALLBACK_URL: <% URL %>/api/auth/callback/google
  GITHUB_CALLBACK_URL: <% URL %>/api/auth/callback/github

  # OAuth secrets (keep same values)
  GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
  GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
  GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
  GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
```

---

## Migration Checklist

### Before Migration
- [ ] Export all environment variables from current platform
- [ ] Document current database schema
- [ ] List all external services (Stripe, OAuth, etc.)
- [ ] Create database backup
- [ ] Note current domain/URLs for updating third-party configs

### During Migration
- [ ] Clone code repository
- [ ] Create Dockerfile (if missing)
- [ ] Build for `linux/amd64`
- [ ] Push to `registry.nexlayer.io`
- [ ] Create `nexlayer.yaml`
- [ ] Validate with `nexlayer_validate_yaml`
- [ ] Deploy with `nexlayer_deploy`
- [ ] Import database with `pg_restore`

### After Migration
- [ ] Update Stripe webhook endpoints
- [ ] Update OAuth callback URLs
- [ ] Update DNS records (if custom domain)
- [ ] Test all critical flows
- [ ] Monitor logs for errors
- [ ] Disable/delete old deployment

---

## Troubleshooting

### Database Won't Initialize
```
❌ Error: initdb - directory /var/lib/postgresql/data is not empty
```
**Fix**: Mount the volume at `/var/lib/postgresql/data` and set `PGDATA: /var/lib/postgresql/data/pgdata` so the data directory lives in the `pgdata` subdirectory, clear of `lost+found` at the mount root.

### pg_restore Fails
```
❌ Error: pg_restore: error: connection to server failed
```
**Fix**: Ensure database pod is running first. Check `nexlayer_check_deployment_status`.

### Stripe Webhooks Return 400
```
❌ Webhook signature verification failed
```
**Fix**: You're using the old webhook secret. Get the new one from Stripe Dashboard.

### OAuth "Redirect URI Mismatch"
```
❌ Error: redirect_uri_mismatch
```
**Fix**: Add your Nexlayer URL to the OAuth provider's authorized redirect URIs.

### Image Pull Failed
```
❌ Error: ImagePullBackOff
```
**Fixes**:
- Ensure image tag exists: `docker push registry.nexlayer.io/YOUR_USER_ID/app:v1`
- Re-run `nexlayer_build_and_push_image` to get a fresh JWT, then `echo "$NEXLAYER_JWT" | docker login registry.nexlayer.io -u oauth2accesstoken --password-stdin`
- Verify image is `linux/amd64`: `docker build --platform linux/amd64`

---

## Sources

- [Disco: Migrate from Vercel](https://disco.cloud/blog/migrate-your-nextjs-app-from-vercel-to-your-own-infrastructure/)
- [Lee Robinson's Next.js Self-Host Example](https://github.com/leerob/next-self-host)
- [Railway: Migrate from Render](https://docs.railway.com/migration/migrate-from-render)
- [Railway: PostgreSQL Guide](https://docs.railway.com/guides/postgresql)
- [Render: Docker Deployment](https://render.com/docs/docker)
- [Fly.io: Kubernetes Docs](https://fly.io/docs/kubernetes/)
- [DigitalOcean: PostgreSQL Migration](https://docs.digitalocean.com/products/databases/postgresql/how-to/migrate/)
- [Lovable: GitHub Integration](https://docs.lovable.dev/integrations/github)
- [Hackclub: Replit Lifeboat Exporter](https://github.com/hackclub/replit-lifeboat)
- [Base44: Export Limitations](https://shipper.now/export-code-base44/)
- [PostgreSQL Docker Backup Guide](https://simplebackups.com/blog/docker-postgres-backup-restore-guide-with-examples/)
- [Stripe: Multi-Environment Webhook Handler](https://github.com/adshrc/stripe-multi-environment-webhook-handler)
