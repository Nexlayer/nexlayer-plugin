# Troubleshooting Guide

Common issues and solutions for Nexlayer deployments.

## Launchfile Validation Errors

### Invalid Application Name

**Error:** `Application name must match pattern ^[a-z][a-z0-9.-]{2,63}$`

**Cause:** Name contains invalid characters or format.

**Solution:**
```yaml
# Wrong
name: MyApp
name: 1-app
name: my_app
name: ab

# Correct
name: my-app
name: myapp
name: my-app.v2
```

### Missing Path Field

**Error:** `At least one pod must include the 'path' field`

**Cause:** No pod has a web-facing route defined.

**Solution:** Add `path: /` to your main web-facing pod:
```yaml
pods:
  - name: web
    image: nginx:latest
    path: /          # Add this
    servicePorts: [80]
```

### Invalid Image Format

**Error:** `Image must include tag`

**Cause:** Docker image doesn't include a version tag.

**Solution:**
```yaml
# Wrong
image: nginx
image: postgres

# Correct
image: nginx:latest
image: postgres:16
image: node:20-alpine
```

### Invalid Port Number

**Error:** `Port must be between 1 and 65535`

**Solution:** Use valid port numbers:
```yaml
# Wrong
servicePorts: [0]
servicePorts: [70000]

# Correct
servicePorts: [80]
servicePorts: [3000]
servicePorts: [8080, 8443]
```

## Pod Communication Issues

### Pod Can't Connect to Database

**Symptom:** Connection refused or timeout errors.

**Cause:** Using wrong hostname format.

**Solution:** Use the `.pod` suffix for inter-pod communication:
```yaml
# Wrong
DATABASE_URL: postgresql://user:pass@localhost:5432/db
DATABASE_URL: postgresql://user:pass@postgres:5432/db

# Correct
DATABASE_URL: postgresql://user:pass@postgres.pod:5432/db
```

### Service Discovery Not Working

**Symptom:** DNS resolution fails for pod names.

**Cause:** Pod name doesn't match or typo in hostname.

**Solution:** Ensure pod names match exactly:
```yaml
pods:
  - name: api          # This name...
    image: my-api:latest
    servicePorts: [8000]

  - name: frontend
    image: my-frontend:latest
    vars:
      API_URL: http://api.pod:8000  # ...must match here
```

## Database Issues

### PostgreSQL Won't Start

**Symptom:** PostgreSQL container exits immediately or shows initialization errors.

**Cause:** Volume mounted to `/var/lib/postgresql/data` without moving PGDATA into the `pgdata` subdirectory, so the data directory sits at the mount root next to `lost+found`.

**Solution:**
```yaml
# Wrong - data dir at mount root, initialization fails
vars:
  PGDATA: /var/lib/postgresql/data
volumes:
  - name: postgres-data
    size: 10Gi
    mountPath: /var/lib/postgresql/data

# Correct - data dir lives in pgdata subdirectory via PGDATA
vars:
  PGDATA: /var/lib/postgresql/data/pgdata
volumes:
  - name: postgres-data
    size: 10Gi
    mountPath: /var/lib/postgresql/data
```

**Why:** The platform creates a `lost+found` directory in mounted volumes, which conflicts with PostgreSQL's initialization that expects an empty data directory. Pointing PGDATA at the `pgdata` subdirectory keeps the data directory clear of `lost+found`.

### Database Connection Pool Exhausted

**Symptom:** "Too many connections" errors.

**Solution:** Configure connection limits in your application:
```yaml
vars:
  DATABASE_URL: postgresql://user:pass@db.pod:5432/mydb?pool_size=10
```

Or increase PostgreSQL max connections:
```yaml
- name: postgres
  image: postgres:16
  vars:
    POSTGRES_MAX_CONNECTIONS: "200"
```

## Image Pull Issues

### Image Pull Failed - Not Found

**Symptom:** `ImagePullBackOff` or `ErrImagePull`

**Causes:**
1. Image tag doesn't exist
2. Typo in image name
3. Private image without credentials

**Solutions:**

1. Verify image exists:
   ```bash
   docker pull nginx:latest
   ```

2. Check spelling and tag:
   ```yaml
   # Verify these are correct
   image: nginx:latest
   image: postgres:16
   ```

3. For private images, add registry credentials:
   ```yaml
   registryLogin:
     registry: ghcr.io
     username: my-org
     personalAccessToken: ghp_xxxx
   pods:
     - name: app
       image: ghcr.io/my-org/my-app:latest
   ```

### Private Registry Authentication Failed

**Symptom:** `unauthorized` or `authentication required`

**Solution:** Verify credentials:
```yaml
registryLogin:
  registry: ghcr.io               # Must match image registry
  username: my-org                # Your org or username
  personalAccessToken: ghp_xxxx   # Token with read:packages scope
```

For GitHub Container Registry, create a token with:
- `read:packages` permission
- Access to the specific repository

## Volume Issues

### Volume Mount Conflicts

**Symptom:** Pod fails to start with mount conflict error.

**Cause:** Multiple volumes or secrets using the same mountPath.

**Solution:** Use unique paths:
```yaml
# Wrong - same mountPath
volumes:
  - name: data1
    mountPath: /data
  - name: data2
    mountPath: /data

# Correct - unique paths
volumes:
  - name: data1
    mountPath: /data/primary
  - name: data2
    mountPath: /data/secondary
```

### Persistent Data Lost

**Symptom:** Data disappears after redeployment.

**Cause:** Volume not configured or wrong mountPath.

**Solution:** Ensure volume is properly configured:
```yaml
volumes:
  - name: my-data
    size: 10Gi
    mountPath: /app/data  # Must match where app writes
```

## Secrets Issues

### Secret File Not Found

**Symptom:** Application can't find secret file.

**Cause:** Looking in wrong path.

**Default path:** If `mountPath` not specified, secrets are at `/var/secrets/<name>/`

**Solution:** Specify explicit mountPath:
```yaml
secrets:
  - name: api-key
    data: sk-xxxxx
    fileName: api.key
    mountPath: /var/secrets  # File will be at /var/secrets/api.key
```

### JSON/YAML Secret Corrupted

**Symptom:** Secret file has wrong content or format.

**Cause:** Not base64 encoding structured data.

**Solution:** Base64 encode JSON/YAML:
```bash
# Encode your JSON
echo '{"api_key": "sk-123"}' | base64
# Result: eyJhcGlfa2V5IjogInNrLTEyMyJ9Cg==
```

```yaml
secrets:
  - name: credentials
    data: eyJhcGlfa2V5IjogInNrLTEyMyJ9Cg==
    fileName: credentials.json
    mountPath: /var/secrets
```

## Network Issues

### 404 Not Found on All Routes

**Symptom:** All requests return 404.

**Cause:** No pod has `path: /` defined.

**Solution:** Add path to your main web pod:
```yaml
- name: frontend
  image: my-app:latest
  path: /              # Required for root routing
  servicePorts: [3000]
```

### CORS Errors

**Symptom:** Browser blocks requests with CORS errors.

**Cause:** Backend not configured for correct origin.

**Solution:** Use `<% URL %>` variable for dynamic origin:
```yaml
- name: api
  image: my-api:latest
  vars:
    CORS_ORIGIN: <% URL %>
    ALLOWED_ORIGINS: <% URL %>
```

### Health Check Failures

**Symptom:** Pod repeatedly restarts or shows unhealthy.

**Cause:** Application not responding on expected port.

**Solutions:**

1. Ensure app binds to `0.0.0.0`, not `localhost`:
   ```yaml
   vars:
     HOST: 0.0.0.0
     PORT: "8000"
   ```

2. Verify servicePorts match application:
   ```yaml
   servicePorts: [8000]  # Must match app's listening port
   ```

## Resource Issues

### Out of Memory

**Symptom:** Pod killed with OOMKilled status.

**Solution:** Increase memory limits in application or optimize usage:
```yaml
vars:
  NODE_OPTIONS: --max-old-space-size=512
  JAVA_OPTS: -Xmx512m
```

### Slow Startup

**Symptom:** Pod takes very long to become ready.

**Cause:** Large images or slow initialization.

**Solutions:**

1. Use smaller base images:
   ```yaml
   # Instead of full image
   image: node:20

   # Use slim/alpine
   image: node:20-alpine
   ```

2. For ML models, pre-download during build, not runtime.

## Deployment Issues

### Deployment URL Not Working

**Symptom:** Deployment URL no longer works.

**Solution:** Redeploy your application. For custom domain deployments, add `url` field:
```yaml
application:
  name: my-app
  url: app.example.com  # Uses your custom domain
  pods: [...]
```

### Custom Domain Not Working

**Symptom:** Custom domain doesn't resolve.

**Solutions:**

1. Verify DNS is configured:
   - Add CNAME record pointing to Nexlayer
   - Allow DNS propagation (up to 48 hours)

2. Ensure domain format is valid:
   ```yaml
   # Correct
   url: app.example.com
   url: api.mysite.io

   # Wrong
   url: https://app.example.com  # No protocol
   url: example.com/app          # No paths
   ```

## Debugging Tips

### View Deployment Logs

Using MCP:
```
Show me the logs from my Nexlayer deployment
```

### Check Pod Status

Using MCP:
```
What's the status of my pods on Nexlayer?
```

### Validate Launchfile Locally

Before deploying, check YAML syntax:
```bash
# Using yq
yq eval nexlayer.yaml

# Using Python
python -c "import yaml; yaml.safe_load(open('nexlayer.yaml'))"
```

### Test Image Locally

```bash
# Test if image runs
docker run --rm -p 3000:3000 my-image:latest

# Check if it's accessible
curl http://localhost:3000
```
