# Migration Reference

Moving an app that runs somewhere else onto Nexlayer.

Any app that runs in a container runs on Nexlayer. The pattern is the same regardless of where it lives today.

| What you have today | What it becomes here | Effort |
|---------------------|----------------------|--------|
| Git repo, no Dockerfile | Generated Dockerfile + `nexlayer.yaml` | Easy |
| Git repo with Dockerfile | `nexlayer.yaml` only | Easy |
| Host-specific config file (`*.json`, `*.toml`) | `nexlayer.yaml` pods + servicePorts | Easy |
| Managed Postgres | `postgres` pod + `pg_dump`/`pg_restore`, or keep it external | Medium |
| Managed Redis / queue | `redis` pod, or keep it external via env var | Medium |
| Serverless functions | One API pod that owns those routes | Medium |

### Universal Migration Pattern

```
1. Get the code into a Git repository
2. Export the database (pg_dump) if you are moving it
3. Create a Dockerfile (see references/DOCKERFILES.md) if missing
4. Build: docker build --platform linux/amd64 -t registry.nexlayer.io/<app>/<pod>:latest .
5. Push:  docker push registry.nexlayer.io/<app>/<pod>:latest
6. Write nexlayer.yaml (see templates/)
7. Validate: nexlayer_validate_yaml
8. Deploy: nexlayer_deploy
9. Import data: pg_restore
10. Update webhooks and OAuth callbacks to the new URL
```

**Keep managed services external when it is cheaper to.** Point an env var at the existing provider instead of self-hosting it — see the External Services section above.
