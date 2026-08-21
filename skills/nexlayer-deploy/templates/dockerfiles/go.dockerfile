# ============================================================================
# GO DOCKERFILE - Multi-stage Production Build
# ============================================================================
# Framework: Any Go framework (Gin, Echo, Fiber, Chi, stdlib)
# Output: Static binary
# Port: 8080
# ============================================================================

# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app

# Install git for private dependencies
RUN apk add --no-cache git

# Download dependencies first (better caching)
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o main .

# Production stage - minimal image
FROM alpine:latest
WORKDIR /app

# Install CA certificates for HTTPS
RUN apk --no-cache add ca-certificates tzdata

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy binary from builder
COPY --from=builder /app/main .

# Copy any static assets if they exist
COPY --from=builder /app/static ./static 2>/dev/null || true
COPY --from=builder /app/templates ./templates 2>/dev/null || true
COPY --from=builder /app/public ./public 2>/dev/null || true

RUN chown -R appuser:appgroup /app

USER appuser

ENV PORT=8080

EXPOSE 8080

CMD ["./main"]
