# ============================================================================
# RUST DOCKERFILE - Multi-stage Production Build
# ============================================================================
# Framework: Actix-web, Axum, Rocket, Warp, or any Rust web framework
# Output: Static binary
# Port: 8080
# ============================================================================

# Build stage
FROM rust:1.75-alpine AS builder
WORKDIR /app

# Install musl-dev for static linking
RUN apk add --no-cache musl-dev

# Create a dummy project to cache dependencies
RUN cargo new --bin temp
WORKDIR /app/temp
COPY Cargo.toml Cargo.lock ./
RUN cargo build --release && rm -rf src

# Now copy real source and build
WORKDIR /app
COPY . .
RUN cargo build --release

# Production stage - minimal image
FROM alpine:latest
WORKDIR /app

# Install CA certificates
RUN apk --no-cache add ca-certificates tzdata

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy binary (find the binary name from Cargo.toml)
COPY --from=builder /app/target/release/*[!.d] ./app 2>/dev/null || \
     COPY --from=builder /app/target/release/$(grep -m1 'name' /app/Cargo.toml | cut -d'"' -f2) ./app

# Copy static assets if they exist
COPY --from=builder /app/static ./static 2>/dev/null || true
COPY --from=builder /app/templates ./templates 2>/dev/null || true
COPY --from=builder /app/public ./public 2>/dev/null || true

RUN chown -R appuser:appgroup /app

USER appuser

ENV PORT=8080
ENV RUST_LOG=info

EXPOSE 8080

CMD ["./app"]
