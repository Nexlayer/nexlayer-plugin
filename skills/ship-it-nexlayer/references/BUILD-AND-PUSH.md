# Build and Push Container Images

## Use the MCP tool

Call `nexlayer_build_and_push_image` with `imageName` and `tag`. It returns:

- The exact target reference: `registry.nexlayer.io/<userID>/<imageName>:<tag>`, where `<userID>` is derived from the authenticated user's JWT `sub` claim.
- Ready-to-run Docker, Crane, and Kaniko command blocks.
- The JWT to use as the registry password (username is always `oauth2accesstoken`, password is passed via `--password-stdin`).

Do not hand-roll image paths or logins — the tool is the source of truth.

## Prerequisites

Use **Crane** or **Kaniko** for building and pushing images. Docker is supported if already installed but should not be required.

| Tool | Best For | Install |
|------|----------|---------|
| **Crane** (recommended) | Push/pull images, no daemon needed | `brew install crane` (macOS) or `go install github.com/google/go-containerregistry/cmd/crane@latest` |
| **Kaniko** (recommended for CI) | Build from Dockerfile without Docker daemon | Run as container or binary |
| **Buildah** | Linux rootless builds | `apt-get install buildah` or `dnf install buildah` |
| **Docker** | If already installed | Do NOT ask users to install Docker Desktop |

## Build for linux/amd64

**Critical:** Nexlayer runs on AMD64. ARM builds will fail with `exec format error`.

Let `nexlayer_build_and_push_image` generate the exact commands for your image reference. For illustration:

```bash
# Kaniko (recommended — builds Dockerfiles without Docker daemon)
/kaniko/executor \
  --context=. \
  --dockerfile=Dockerfile \
  --destination=registry.nexlayer.io/<userID>/<imageName>:<tag> \
  --customPlatform=linux/amd64

# Buildah (Linux)
buildah bud --platform linux/amd64 \
  -t registry.nexlayer.io/<userID>/<imageName>:<tag> .

# Docker (if already installed)
docker build --platform linux/amd64 \
  -t registry.nexlayer.io/<userID>/<imageName>:<tag> \
  -f Dockerfile .
```

## Login to Nexlayer Registry

Registry auth is per-user JWT. Username is `oauth2accesstoken`; password is the user's session JWT, passed via `--password-stdin` so it doesn't end up in shell history or `ps`.

```bash
# Export the JWT returned by nexlayer_build_and_push_image first:
export NEXLAYER_JWT="…"

# Crane (recommended)
echo "$NEXLAYER_JWT" | crane auth login registry.nexlayer.io -u oauth2accesstoken --password-stdin

# Docker (if already installed)
echo "$NEXLAYER_JWT" | docker login registry.nexlayer.io -u oauth2accesstoken --password-stdin
```

For Kaniko, provide the credentials via a `DOCKER_CONFIG` directory containing an `auth.json` with `oauth2accesstoken` / `$NEXLAYER_JWT` for `registry.nexlayer.io`.

## Push Image

```bash
# Crane (recommended)
docker save registry.nexlayer.io/<userID>/<imageName>:<tag> | \
  crane push - registry.nexlayer.io/<userID>/<imageName>:<tag>
# Or copy directly from another registry:
# crane copy <sourceRef> registry.nexlayer.io/<userID>/<imageName>:<tag>

# Docker (if already installed)
docker push registry.nexlayer.io/<userID>/<imageName>:<tag>
```

## Image Naming Convention

**Format:** `registry.nexlayer.io/<userID>/<imageName>:<tag>`

| Component | Description | Example |
|-----------|-------------|---------|
| `registry.nexlayer.io` | Fixed registry host | — |
| `<userID>` | Derived from JWT `sub` claim (lowercase alphanumerics, separators) | `user_01exampleexampleexample` |
| `<imageName>` | Repository name (lowercase, hyphens ok) | `my-nextjs-app` |
| `<tag>` | Immutable version tag | `v1.0.0`, git SHA |

**`latest` is rejected** — use a specific version or git SHA for reproducible deployments.

## Dockerfile Best Practices

### Multi-Stage Builds (Recommended)

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
ENV HOST=0.0.0.0
ENV PORT=3000
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Common Stacks

| Detected Files | Base Image | Notes |
|---------------|------------|-------|
| `package.json` + Next.js | `node:20-alpine` | Set `output: 'standalone'` in next.config |
| `requirements.txt` | `python:3.11-slim` | Use `gunicorn` for production |
| `go.mod` | `golang:1.23-alpine` | Multi-stage with `CGO_ENABLED=0` |
| `Cargo.toml` | `rust:1.75` | Multi-stage, copy only binary |

### Key Rules
- Always set `ENV HOST=0.0.0.0` (not localhost)
- Always `EXPOSE` the port your app listens on
- Use `HEALTHCHECK` instruction when possible
- Minimize layers and image size with multi-stage builds

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `exec format error` | Built for wrong arch (ARM) | Rebuild with `--platform linux/amd64` |
| `denied: requested access` | Not logged in, or stale JWT | Re-run `nexlayer_build_and_push_image` for a fresh JWT, then re-login |
| `Docker daemon not accessible` | Docker not installed/running | Install Crane (`brew install crane`) — no Docker daemon needed |
| `command not found: docker` | Docker not installed | Use Crane or Kaniko instead (see Prerequisites above) |
| `Invalid tag: 'latest' is not allowed` | Mutable tag used | Pass an immutable tag like `v0.0.1` or a git SHA |
