# ============================================================================
# PHOENIX/ELIXIR DOCKERFILE - Production Release
# ============================================================================
# Framework: Phoenix
# Output: Elixir release
# Port: 4000
# ============================================================================

# Build stage
FROM elixir:1.16-alpine AS builder
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base git npm

# Install hex and rebar
RUN mix local.hex --force && \
    mix local.rebar --force

# Set environment
ENV MIX_ENV=prod

# Install dependencies
COPY mix.exs mix.lock ./
RUN mix deps.get --only prod
RUN mix deps.compile

# Copy application
COPY . .

# Compile assets if present
RUN if [ -f assets/package.json ]; then \
      cd assets && npm ci && npm run deploy && cd ..; \
    fi
RUN mix phx.digest 2>/dev/null || true

# Create release
RUN mix release

# Production stage
FROM alpine:latest
WORKDIR /app

RUN apk add --no-cache libstdc++ openssl ncurses-libs

# Get the app name from mix.exs
COPY --from=builder /app/_build/prod/rel/* ./

ENV PHX_HOST=0.0.0.0
ENV PORT=4000

EXPOSE 4000

CMD ["bin/$(ls bin | head -1)", "start"]
