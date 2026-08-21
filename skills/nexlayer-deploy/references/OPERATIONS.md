# Operations Reference

External managed services, custom domains, and private registries.

## External Services (No Self-Hosting)

```yaml
vars:
  # Supabase
  SUPABASE_URL: ${SUPABASE_URL}
  SUPABASE_KEY: ${SUPABASE_KEY}

  # Neon (PostgreSQL)
  DATABASE_URL: ${NEON_DATABASE_URL}

  # Pinecone
  PINECONE_API_KEY: ${PINECONE_API_KEY}

  # OpenAI
  OPENAI_API_KEY: ${OPENAI_API_KEY}

  # Stripe
  STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
```

---

## Production (Custom Domain)

```yaml
application:
  name: my-production-app
  url: app.example.com          # Add this for permanent deployment
  pods:
    - name: web
      image: my-app:v1.0.0      # Use specific version, not :latest
      path: /
      servicePorts: [80]
      secrets:                   # Use secrets, not vars for sensitive data
        - name: api-key
          data: ${API_KEY}
          fileName: api.key
          mountPath: /var/secrets
```

---

## Private Registry

```yaml
application:
  name: my-private-app
  registryLogin:
    registry: ghcr.io
    username: my-org
    personalAccessToken: ${GITHUB_TOKEN}
  pods:
    - name: app
      image: ghcr.io/my-org/my-app:v1.0.0
      path: /
      servicePorts: [3000]
```
