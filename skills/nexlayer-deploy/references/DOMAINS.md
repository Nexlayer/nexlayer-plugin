# Custom Domains Skill

> Load this skill when user wants to use their own domain instead of the default Nexlayer URL

---

## Quick Decision Tree

```
Custom Domain Request
│
├─→ First time setup?
│   └─→ GO TO: Full Setup Flow
│
├─→ Domain already added but not working?
│   └─→ GO TO: Verify Nameservers
│
├─→ Subdomain setup (app.example.com)?
│   └─→ GO TO: Subdomain Configuration
│
└─→ Multiple apps on one domain?
    └─→ GO TO: Path-Based Routing
```

---

## Full Setup Flow

### Step 1: Check Current Configuration

```bash
TOOL: nexlayer_check_domain_configuration
  └─→ rootDomain: "example.com"
```

**Possible Results**:
- Domain not found → Continue to Step 2
- Domain found, not verified → Skip to Step 3
- Domain found, verified → Skip to Step 4

### Step 2: Add Domain to Profile

```bash
TOOL: nexlayer_add_domain_to_profile
  └─→ rootDomain: "example.com"  # Root domain only, not subdomain
```

**Important**: Use the root domain (example.com), not subdomains (app.example.com)

### Step 3: Configure Nameservers

**User Action Required**: Update nameservers at domain registrar

```
Current Nameservers: (varies by registrar)
New Nameservers:
  └─→ ns3.nexlayer.io
  └─→ ns4.nexlayer.io
```

**Common Registrars**:

| Registrar | Where to Change |
|-----------|-----------------|
| GoDaddy | Domain Settings → Nameservers → Change |
| Namecheap | Domain List → Manage → Nameservers → Custom DNS |
| Cloudflare | Remove from Cloudflare, use Nexlayer NS |
| Google Domains | DNS → Name servers → Custom |
| Route53 | Hosted Zone → NS records |

**Wait Time**: DNS propagation takes 5 minutes to 48 hours (usually ~30 min)

### Step 4: Verify Nameservers

```bash
TOOL: nexlayer_verify_name_servers_configuration
  └─→ rootDomain: "example.com"
```

**Possible Results**:
- ✅ Verified → Domain ready to use
- ❌ Not verified → Wait longer or check registrar settings

### Step 5: Deploy with Custom Domain

Update your `nexlayer.yaml`:

```yaml
application:
  name: my-app
  domain: app.example.com  # Add this line
  pods:
    - name: web
      image: registry.nexlayer.io/my-app/web:latest
      path: /
      servicePorts: [3000]
```

Then deploy:

```bash
TOOL: nexlayer_deploy
  └─→ yamlContent: "..." (your YAML with domain)
```

---

## Verify Nameservers

If domain was added but not working:

```bash
# 1. Check current status
TOOL: nexlayer_check_domain_configuration
  └─→ rootDomain: "example.com"

# 2. If not verified, verify nameservers
TOOL: nexlayer_verify_name_servers_configuration
  └─→ rootDomain: "example.com"
```

### Troubleshooting Verification Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| Still showing old NS | DNS not propagated | Wait 30min - 48hrs |
| Wrong NS configured | Typo in registrar | Check: ns3.nexlayer.io, ns4.nexlayer.io |
| Partial propagation | Some DNS servers updated | Wait longer |
| Cloudflare conflict | Domain still on Cloudflare | Remove from CF dashboard |

### Check DNS Propagation

Tell user to check propagation status:
```
https://www.whatsmydns.net/#NS/example.com
```

Should show `ns3.nexlayer.io` and `ns4.nexlayer.io` globally.

---

## Subdomain Configuration

### Single Subdomain

```yaml
application:
  name: my-app
  domain: app.example.com  # Subdomain
  pods:
    - name: web
      path: /
      # ...
```

### Multiple Subdomains (Different Apps)

Deploy each app with its own subdomain:

**App 1 (api.example.com)**:
```yaml
application:
  name: my-api
  domain: api.example.com
  pods:
    - name: api
      path: /
      # ...
```

**App 2 (dashboard.example.com)**:
```yaml
application:
  name: my-dashboard
  domain: dashboard.example.com
  pods:
    - name: frontend
      path: /
      # ...
```

---

## Path-Based Routing

### Multiple Services on One Domain

If you need `example.com/` and `example.com/api` on the same domain:

```yaml
application:
  name: fullstack-app
  domain: example.com
  pods:
    # Frontend at root
    - name: frontend
      image: registry.nexlayer.io/app/frontend:latest
      path: /
      servicePorts: [3000]

    # API at /api
    - name: api
      image: registry.nexlayer.io/app/api:latest
      path: /api
      servicePorts: [8080]
```

### Path Priority

Paths are matched by specificity:
1. `/api/v2` (most specific)
2. `/api`
3. `/` (catch-all)

---

## Domain Configuration Reference

### YAML Domain Field

```yaml
application:
  name: my-app
  domain: app.example.com  # Optional - use your custom domain
  #        │
  #        └─→ Must be a subdomain of a verified root domain
  #            Root domain (example.com) must be verified first
```

### What Happens Without Domain Field

```yaml
application:
  name: my-app
  # No domain field
  pods: [...]
```

Result: App deployed at `https://my-app-abc123.nexlayer.dev` (auto-generated)

### What Happens With Domain Field

```yaml
application:
  name: my-app
  domain: app.example.com
  pods: [...]
```

Result: App deployed at `https://app.example.com`

---

## SSL/TLS Certificates

**Automatic**: Nexlayer automatically provisions and renews SSL certificates for custom domains using Let's Encrypt.

**Timeline**:
- Certificate provisioned: Within 5 minutes of first request
- Certificate renewal: Automatic before expiry

**No Action Required**: HTTPS just works.

---

## Quick Reference

### MCP Tools for Domains

| Tool | Purpose |
|------|---------|
| `nexlayer_get_domain_setup_guide` | Get setup instructions |
| `nexlayer_check_domain_configuration` | Check if domain is configured |
| `nexlayer_add_domain_to_profile` | Add domain to your profile |
| `nexlayer_verify_name_servers_configuration` | Verify NS are configured |

### Required Nameservers

```
ns3.nexlayer.io
ns4.nexlayer.io
```

### Domain Field Placement

```yaml
application:
  name: my-app
  domain: your-domain.com  # ← Here, at application level
  pods:
    # ...
```
