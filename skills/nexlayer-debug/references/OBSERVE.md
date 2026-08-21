# Observe Skill

> Load this skill when user wants to monitor, inspect, or understand their deployment

---

## Quick Decision Tree

```
Observation Request
│
├─→ "Is my app running?"
│   └─→ GO TO: Deployment Status
│
├─→ "What's in the logs?"
│   └─→ GO TO: Container Logs
│
├─→ "What events happened?"
│   └─→ GO TO: Cluster Events
│
├─→ "Why did it restart?"
│   └─→ GO TO: Crash Investigation
│
└─→ "What's the current config?"
    └─→ GO TO: Configuration Review
```

---

## Deployment Status

### Check All Pods

```bash
TOOL: nexlayer_check_deployment_status
  └─→ applicationName: "your-app"
```

### Understanding Status Response

```
Pod Statuses:
├── Running     → Pod is healthy, containers running
├── Pending     → Pod waiting for resources/scheduling
├── Error       → Pod failed to start
├── Unknown     → Status cannot be determined
└── Terminating → Pod being deleted

Container Statuses:
├── Running     → Container executing
├── Waiting     → Container not yet started
├── Terminated  → Container finished/crashed
```

### Interpreting Results

| Status | Ready | Meaning | Action |
|--------|-------|---------|--------|
| Running | Yes | Healthy | None needed |
| Running | No | Starting up | Wait or check logs |
| Pending | - | Waiting | Check events |
| Error | - | Failed | Check logs |

---

## Container Logs

### Get Current Logs

```bash
TOOL: nexlayer_get_deployment_logs
  └─→ applicationName: "your-app"
  └─→ pods: [{"podName": "api", "previous": false}]
```

### Get Previous Instance Logs (After Crash)

```bash
TOOL: nexlayer_get_deployment_logs
  └─→ applicationName: "your-app"
  └─→ pods: [{"podName": "api", "previous": true}]
```

### Get Multiple Pods at Once

```bash
TOOL: nexlayer_get_deployment_logs
  └─→ applicationName: "your-app"
  └─→ pods: [
        {"podName": "frontend", "previous": false},
        {"podName": "api", "previous": false},
        {"podName": "postgres", "previous": false}
      ]
```

### Log Patterns to Look For

| Pattern | Indicates | Action |
|---------|-----------|--------|
| `ECONNREFUSED` | Connection failed | Check target service, use .pod DNS |
| `FATAL` | Critical error | Fix code/config |
| `ERROR` | Application error | Review error context |
| `Listening on` | App started | Success |
| `database connected` | DB connected | Success |
| `OOMKilled` | Out of memory | Increase resources |

---

## Cluster Events

### Get Recent Events

```bash
TOOL: nexlayer_get_deployment_events
  └─→ domain: "your-app.nexlayer.dev"  # or your custom domain
```

### Understanding Events

```
Event Types:
├── Normal    → Informational events
└── Warning   → Issues requiring attention

Common Events:
├── Scheduled         → Pod assigned to node
├── Pulling           → Downloading container image
├── Pulled            → Image download complete
├── Created           → Container created
├── Started           → Container started
├── Unhealthy         → Health check failed
├── BackOff           → Container crashing repeatedly
├── FailedScheduling  → Can't find node for pod
└── FailedMount       → Volume mount failed
```

### Event Patterns

| Event | Cause | Action |
|-------|-------|--------|
| `FailedScheduling` | Resource constraints | Wait or reduce requirements |
| `BackOff` | Container crashing | Check logs |
| `Unhealthy` | Health check failed | Check servicePorts matches app |
| `FailedMount` | Volume issue | Check volume config |
| `ImagePullBackOff` | Can't get image | Verify image URL |

---

## Crash Investigation

### Step 1: Check Current Status

```bash
TOOL: nexlayer_check_deployment_status
  └─→ applicationName: "your-app"
```

Look for pods with:
- Status: `Error` or `CrashLoopBackOff`
- Ready: `false`
- Restart count > 0

### Step 2: Get Crash Logs

```bash
# Get logs from before the crash
TOOL: nexlayer_get_deployment_logs
  └─→ applicationName: "your-app"
  └─→ pods: [{"podName": "crashing-pod", "previous": true}]
```

### Step 3: Check Events

```bash
TOOL: nexlayer_get_deployment_events
  └─→ domain: "your-app.nexlayer.dev"
```

### Common Crash Causes

| Log Pattern | Cause | Fix |
|-------------|-------|-----|
| `localhost:` | Using localhost | Change to `.pod` DNS |
| `Module not found` | Missing dependency | Fix Dockerfile |
| `Permission denied` | File permissions | Add chmod in Dockerfile |
| `port already in use` | Port conflict | Check servicePorts |
| `Connection refused` | Service not ready | Check service is running |
| Exit code 137 | OOMKilled | Optimize memory usage |
| Exit code 1 | Application error | Fix application bug |

---

## Configuration Review

### Current Schema

```bash
TOOL: nexlayer_get_schema
```

Returns the complete YAML schema with:
- All available fields
- Valid value patterns
- Field descriptions
- Examples

### Validate Current Config

```bash
TOOL: nexlayer_validate_yaml
  └─→ yamlContent: { your yaml as JSON object }
```

---

## Observability Checklist

### Pre-Deploy Check

- [ ] YAML validates without errors
- [ ] All images have `:tag`
- [ ] All pods have `servicePorts`
- [ ] At least one pod has `path`
- [ ] No `localhost` in environment vars
- [ ] Browser vars use `<% URL %>`
- [ ] Server vars use `.pod` DNS
- [ ] PostgreSQL mount is `/var/lib/postgresql`

### Post-Deploy Check

- [ ] All pods show `Running` status
- [ ] All pods show `Ready: true`
- [ ] No warning events in cluster
- [ ] App accessible at URL
- [ ] API endpoints responding
- [ ] Database connections working

---

## Monitoring Commands Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY TOOLS                                            │
├─────────────────────────────────────────────────────────────────┤
│  nexlayer_check_deployment_status                               │
│  ├─→ Input: applicationName                                     │
│  └─→ Output: Pod status, ready state, restart count             │
│                                                                 │
│  nexlayer_get_deployment_logs                                   │
│  ├─→ Input: applicationName, pods (array)                       │
│  ├─→ previous: false = current, true = before crash             │
│  └─→ Output: Container stdout/stderr                            │
│                                                                 │
│  nexlayer_get_deployment_events                                 │
│  ├─→ Input: domain                                              │
│  └─→ Output: platform events (scheduling, image pulls, etc.)        │
│                                                                 │
│  nexlayer_validate_yaml                                         │
│  ├─→ Input: yamlContent (as JSON)                               │
│  └─→ Output: Validation errors/warnings                         │
│                                                                 │
│  nexlayer_get_schema                                            │
│  └─→ Output: Complete YAML schema reference                     │
└─────────────────────────────────────────────────────────────────┘
```
