# Troubleshooting Reference


> Diagnose and fix Nexlayer deployment failures

---

## Quick Diagnosis Tree

```
Deployment Issue
│
├─► ImagePullBackOff / ErrImagePull
│   └─► GO TO: Image Issues
│
├─► CrashLoopBackOff / Error
│   └─► GO TO: Application Crashes
│
├─► Running but not accessible
│   └─► GO TO: Network Issues
│
├─► Database connection errors
│   └─► GO TO: Database Issues
│
├─► Validation failed
│   └─► GO TO: YAML Issues
│
└─► OOMKilled
    └─► GO TO: Resource Issues
```

---

## Step 1: Get Status

```
TOOL: nexlayer_check_deployment_status
INPUT: applicationName: "your-app"

LOOK FOR:
├── Pod status: Running, Pending, Error, CrashLoopBackOff
├── Ready: true/false
├── Restart count: >0 indicates crashes
└── Events: Recent warnings
```

---

## Image Issues (ImagePullBackOff)

### Symptoms
- Pod status: `ImagePullBackOff` or `ErrImagePull`
- Events: "Failed to pull image"

### Root Causes

| Cause | Check | Fix |
|-------|-------|-----|
| Image doesn't exist | Verify image URL | Rebuild: `nexlayer_build_and_push_image` |
| Typo in image name | Check spelling | Correct image URL |
| Missing `:tag` | Image has no tag | Add `:latest` or specific tag |
| Private registry | No imagePullSecrets | Add registry credentials |
| Build failed | Check build logs | Fix Dockerfile, rebuild |

### Fix Steps

1. **Verify image exists**:
   ```
   Image should be: registry.nexlayer.io/{app}/{service}:{tag}
   ```

2. **If missing, rebuild**:
   ```
   TOOL: nexlayer_build_and_push_image
   INPUT: repoPath (your project path)
   ```

3. **Update YAML with correct image URL**

4. **Redeploy**

---

## Application Crashes (CrashLoopBackOff)

### Symptoms
- Pod status: `CrashLoopBackOff`
- Restart count increasing
- Container exits immediately

### Get Crash Logs

```
TOOL: nexlayer_get_deployment_logs
INPUT:
  applicationName: "your-app"
  pods: [{"podName": "api", "previous": true}]  # previous: true for crashed instance
```

### Common Crashes

| Log Pattern | Cause | Fix |
|-------------|-------|-----|
| `ECONNREFUSED localhost:5432` | Using localhost | Change to `postgres.pod:5432` |
| `ECONNREFUSED 127.0.0.1` | Using loopback | Change to `{service}.pod:{port}` |
| `MODULE_NOT_FOUND` | Missing dependency | Check Dockerfile, rebuild |
| `ENOENT` | File not found | Verify file paths in Dockerfile |
| `permission denied` | File permissions | Add `chmod` in Dockerfile |
| Exit code 137 | OOMKilled | Increase memory or optimize |
| Exit code 1 | App error | Check app logs, fix code |

### THE #1 CRASH: localhost

```yaml
# ❌ WRONG - Container can't reach localhost
DATABASE_URL: postgresql://user:pass@localhost:5432/db
REDIS_URL: redis://localhost:6379

# ✅ FIX - Use internal DNS
DATABASE_URL: postgresql://user:pass@postgres.pod:5432/db
REDIS_URL: redis://redis.pod:6379
```

**Why**: Inside a container, `localhost` = this container only. Other services are NOT on localhost.

---

## Network Issues (Not Accessible)

### Symptoms
- Pod is `Running` and `Ready`
- Browser shows error
- `ERR_NAME_NOT_RESOLVED` in console
- API calls fail

### Root Causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| No pods have `path` | No external routing | Add `path: /` to frontend |
| `ERR_NAME_NOT_RESOLVED` | Browser var uses .pod | Use `<% URL %>` for browser vars |
| 502 Bad Gateway | Wrong port | Match `servicePorts` to app port |
| 404 on paths | Missing path config | Add `path: /api` to API pod |
| CORS errors | Cross-origin blocked | Configure CORS in API |

### Browser vs Server URL Fix

```yaml
# ❌ WRONG - Browser can't resolve .pod DNS
NEXT_PUBLIC_API_URL: http://api.pod:8080
REACT_APP_API_URL: http://api.pod:8080

# ✅ FIX - Browser needs public URL
NEXT_PUBLIC_API_URL: <% URL %>/api
REACT_APP_API_URL: <% URL %>/api
```

**Why**: Browser code runs on user's machine. User's machine doesn't know what `.pod` means.

---

## Database Issues

### Symptoms
- API crashes on startup
- "Connection refused" to database
- "Authentication failed"

### PostgreSQL Specific

| Error | Cause | Fix |
|-------|-------|-----|
| `initdb: directory not empty` | Wrong mount path | Use `/var/lib/postgresql` NOT `/data` |
| `connection refused` | DB not ready | Ensure postgres pod is Running |
| `password authentication failed` | Wrong credentials | Verify POSTGRES_USER/PASSWORD match |
| `database does not exist` | Missing POSTGRES_DB | Add `POSTGRES_DB: appname` |

### PostgreSQL Mount Path (CRITICAL)

```yaml
# ❌ WRONG - the platform creates lost+found, breaks initdb
volumes:
  - name: pg-data
    mountPath: /var/lib/postgresql/data

# ✅ FIX - PostgreSQL creates /data itself
volumes:
  - name: pg-data
    mountPath: /var/lib/postgresql
```

### Connection String Format

```
postgresql://{USER}:{PASSWORD}@{POD}.pod:{PORT}/{DATABASE}
            ^^^^^^ ^^^^^^^^^^  ^^^^^^^^^^^^ ^^^^ ^^^^^^^^^^
```

Example:
```yaml
DATABASE_URL: postgresql://postgres:postgres@postgres.pod:5432/app
```

---

## Resource Issues (OOMKilled)

### Symptoms
- Exit code 137
- Events show `OOMKilled`
- Pod restarts frequently

### Fix

```yaml
resources:
  requests:
    memory: "256Mi"   # Starting memory
  limits:
    memory: "512Mi"   # Maximum memory
```

### Recommended Memory

| Pod Type | Request | Limit |
|----------|---------|-------|
| Frontend | 128Mi | 256Mi |
| API | 256Mi | 512Mi |
| PostgreSQL | 256Mi | 1Gi |
| Redis | 64Mi | 128Mi |
| Ollama | 4Gi | 8Gi |

---

## YAML Validation Issues

### Run Validation

```
TOOL: nexlayer_validate_yaml
INPUT: yamlContent (as JSON object)
```

### Common Validation Errors

| Error | Fix |
|-------|-----|
| Invalid application.name | Use lowercase, hyphens: `my-app` |
| Invalid pod.name | Use lowercase, hyphens: `api` |
| Missing servicePorts | Add `servicePorts: [port]` |
| Missing image tag | Change `nginx` to `nginx:latest` |
| Invalid volume size | Use `10Gi` not `10GB` |
| No path field | Add `path: /` to at least one pod |

---

## Diagnostic Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TROUBLESHOOTING WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. GET STATUS                                                              │
│     TOOL: nexlayer_check_deployment_status                                  │
│     └─► Identify which pod is failing                                       │
│                                                                             │
│  2. GET LOGS                                                                │
│     TOOL: nexlayer_get_deployment_logs                                      │
│     └─► Set previous: true if pod crashed                                   │
│     └─► Search for error patterns                                           │
│                                                                             │
│  3. GET EVENTS                                                              │
│     TOOL: nexlayer_get_deployment_events                                    │
│     └─► Look for warnings about images, resources                           │
│                                                                             │
│  4. IDENTIFY ROOT CAUSE                                                     │
│     └─► Match error pattern to table above                                  │
│                                                                             │
│  5. FIX                                                                     │
│     └─► Update YAML or Dockerfile                                           │
│     └─► Rebuild if needed                                                   │
│     └─► Validate and redeploy                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Fixes Cheat Sheet

| Error | One-Line Fix |
|-------|--------------|
| localhost in URL | Change `localhost` → `{pod}.pod` |
| .pod in browser var | Change `.pod` → `<% URL %>` |
| ImagePullBackOff | Rebuild with `nexlayer_build_and_push_image` |
| Missing tag | Add `:latest` to image |
| No servicePorts | Add `servicePorts: [port]` |
| PostgreSQL initdb | Mount to `/var/lib/postgresql` |
| OOMKilled | Increase memory limits |
| No path | Add `path: /` to frontend |
