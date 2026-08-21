# ============================================================================
# ASTRO DOCKERFILE - SSR or Static Build
# ============================================================================
# Framework: Astro
# Output: Node.js server (SSR) or static (nginx)
# Port: 4321 (SSR) or 80 (static)
#
# Detects output mode from astro.config
# ============================================================================

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Check if it's SSR or static
RUN if [ -f dist/server/entry.mjs ]; then \
      echo "ssr" > /tmp/mode; \
    else \
      echo "static" > /tmp/mode; \
    fi

# SSR Production stage
FROM node:20-alpine AS ssr
WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
RUN npm ci --only=production

ENV HOST=0.0.0.0
ENV PORT=4321

EXPOSE 4321

CMD ["node", "dist/server/entry.mjs"]

# Static Production stage
FROM nginx:alpine AS static

COPY --from=builder /app/dist /usr/share/nginx/html

RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    location / { \
        try_files $uri $uri/ $uri.html /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
