# ============================================================================
# NODE.JS DOCKERFILE - Express/Fastify/Generic Node
# ============================================================================
# Framework: Express, Fastify, Koa, or vanilla Node.js
# Output: Node.js server
# Port: 3000 (configurable via PORT env)
# ============================================================================

FROM node:20-alpine
WORKDIR /app

# Install dependencies first (better caching)
COPY package*.json ./
COPY yarn.lock* ./
COPY pnpm-lock.yaml* ./

# Install production dependencies
RUN \
  if [ -f pnpm-lock.yaml ]; then \
    corepack enable pnpm && pnpm install --frozen-lockfile --prod; \
  elif [ -f yarn.lock ]; then \
    yarn install --frozen-lockfile --production; \
  else \
    npm ci --only=production; \
  fi

# Copy application source
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nodeuser && \
    chown -R nodeuser:nodejs /app

USER nodeuser

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# Start the application
# Detects: package.json "start" script, or falls back to index.js/server.js/app.js
CMD ["sh", "-c", "if [ -f package.json ] && grep -q '\"start\"' package.json; then npm start; elif [ -f index.js ]; then node index.js; elif [ -f server.js ]; then node server.js; elif [ -f app.js ]; then node app.js; elif [ -f src/index.js ]; then node src/index.js; else echo 'No entry point found' && exit 1; fi"]
