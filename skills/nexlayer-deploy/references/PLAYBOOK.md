# Deployment Failure Playbook

Symptom-first fixes for a deploy that did not come up. For a deployment that was working and broke later, use the `nexlayer-debug` skill.

### Deployment Fails

| Symptom | Check | Fix |
|---------|-------|-----|
| `ImagePullBackOff` | Image exists? | `docker push` with correct tag |
| `CrashLoopBackOff` | Logs | Fix application error |
| `Pending` forever | Resources | Check pod limits |

**Step-by-step:**
1. Check image exists: `docker pull registry.nexlayer.io/nexlayer-mcp/YOUR/app:tag`
2. Verify port matches container's EXPOSE
3. Confirm `servicePorts` in YAML matches app's listen port
4. Check `nexlayer_get_deployment_logs` for errors

### Database Won't Initialize

| Symptom | Cause | Fix |
|---------|-------|-----|
| `initdb: directory not empty` | Wrong mountPath | Use `/var/lib/postgresql` NOT `/data` |
| `FATAL: role does not exist` | Missing env vars | Add `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| `connection refused` | Pod not ready | Wait for pod startup, check logs |

**PostgreSQL checklist:**
```yaml
- name: db
  image: postgres:16
  servicePorts: [5432]
  vars:
    POSTGRES_USER: postgres      # Required
    POSTGRES_PASSWORD: password  # Required
    POSTGRES_DB: app             # Required
  volumes:
    - name: data
      size: 10Gi
      mountPath: /var/lib/postgresql  # NOT /var/lib/postgresql/data
```

### Frontend Can't Reach API

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERR_NAME_NOT_RESOLVED` | Used `.pod` in browser var | Use `<% URL %>` |
| `CORS error` | Missing CORS config | Add `CORS_ORIGIN: <% URL %>` |
| `404 on /api` | API pod missing `path` | Add `path: /api` to backend |

**Browser vs Server rule:**
```yaml
# ❌ WRONG - browser can't resolve .pod
NEXT_PUBLIC_API_URL: http://api.pod:8000

# ✅ RIGHT - browser gets public URL
NEXT_PUBLIC_API_URL: <% URL %>/api
```

### Stripe Webhooks Failing

| Symptom | Cause | Fix |
|---------|-------|-----|
| `400 Bad Request` | Wrong webhook secret | Get new secret from Stripe Dashboard |
| `Signature verification failed` | Old signing secret | Update `STRIPE_WEBHOOK_SECRET` |
| Webhook not received | Old URL | Add new endpoint in Stripe |

**After migration:**
1. Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `<your-nexlayer-url>/api/webhooks/stripe`
3. Copy new signing secret
4. Update nexlayer.yaml: `STRIPE_WEBHOOK_SECRET: ${NEW_SECRET}`
