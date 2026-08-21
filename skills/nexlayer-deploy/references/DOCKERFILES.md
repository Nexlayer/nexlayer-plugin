# Dockerfile Reference

> Ready-to-use Dockerfiles for common frameworks

---

## Quick Selection

| Framework | Jump To |
|-----------|---------|
| Next.js | [Next.js Dockerfile](#nextjs) |
| React (CRA) | [React Dockerfile](#react-cra) |
| React (Vite) | [Vite Dockerfile](#vite) |
| Vue.js | [Vue Dockerfile](#vuejs) |
| Node.js/Express | [Node Dockerfile](#nodejs-express) |
| Python/FastAPI | [FastAPI Dockerfile](#python-fastapi) |
| Python/Django | [Django Dockerfile](#python-django) |
| Python/Flask | [Flask Dockerfile](#python-flask) |
| Go | [Go Dockerfile](#go) |
| Rust | [Rust Dockerfile](#rust) |
| Java/Spring | [Spring Dockerfile](#java-spring) |
| .NET | [.NET Dockerfile](#dotnet) |

---

## Next.js

<a name="nextjs"></a>

### Standalone Build (Recommended)

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app

# Copy standalone build
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

**Required**: Add to `next.config.js`:
```javascript
module.exports = {
  output: 'standalone',
}
```

---

## React (CRA)

<a name="react-cra"></a>

### Multi-stage with nginx

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx config for SPA routing
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Vite

<a name="vite"></a>

### React/Vue/Svelte with Vite

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Vue.js

<a name="vuejs"></a>

### Vue 3 with nginx

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Node.js/Express

<a name="nodejs-express"></a>

### Standard Node.js API

```dockerfile
FROM node:20-alpine
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --production

# Copy source
COPY . .

EXPOSE 3000
CMD ["node", "index.js"]
```

### With TypeScript

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY --from=builder /app/dist ./dist

EXPOSE 3000
CMD ["node", "dist/index.js"]
```

---

## Python/FastAPI

<a name="python-fastapi"></a>

### FastAPI with uvicorn

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### With Poetry

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev --no-interaction

# Copy source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Python/Django

<a name="python-django"></a>

### Django with gunicorn

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
```

---

## Python/Flask

<a name="python-flask"></a>

### Flask with gunicorn

```dockerfile
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

---

## Go

<a name="go"></a>

### Multi-stage Go build

```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

# Production stage
FROM alpine:latest
WORKDIR /app

COPY --from=builder /app/main .

EXPOSE 8080
CMD ["./main"]
```

---

## Rust

<a name="rust"></a>

### Multi-stage Rust build

```dockerfile
# Build stage
FROM rust:1.75-alpine AS builder
WORKDIR /app

# Install musl for static linking
RUN apk add --no-cache musl-dev

COPY Cargo.toml Cargo.lock ./
COPY src ./src

RUN cargo build --release

# Production stage
FROM alpine:latest
WORKDIR /app

COPY --from=builder /app/target/release/myapp .

EXPOSE 8080
CMD ["./myapp"]
```

---

## Java/Spring

<a name="java-spring"></a>

### Spring Boot with Maven

```dockerfile
# Build stage
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app

COPY pom.xml .
RUN mvn dependency:go-offline

COPY src ./src
RUN mvn package -DskipTests

# Production stage
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
```

### Spring Boot with Gradle

```dockerfile
# Build stage
FROM gradle:8-jdk21-alpine AS builder
WORKDIR /app

COPY build.gradle settings.gradle ./
COPY src ./src

RUN gradle build -x test --no-daemon

# Production stage
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
```

---

## .NET

<a name="dotnet"></a>

### .NET 8 Web API

```dockerfile
# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS builder
WORKDIR /app

COPY *.csproj ./
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o out

# Production stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine
WORKDIR /app

COPY --from=builder /app/out .

EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
CMD ["dotnet", "MyApp.dll"]
```

---

## Dockerfile Best Practices

### 1. Use Multi-Stage Builds

```dockerfile
# Build stage - has dev dependencies
FROM node:20-alpine AS builder
# ... build steps

# Production stage - minimal
FROM node:20-alpine
# ... only copy what's needed
```

### 2. Order Layers for Caching

```dockerfile
# Dependencies change less often - cache this layer
COPY package*.json ./
RUN npm ci

# Source changes often - this layer rebuilds
COPY . .
```

### 3. Use .dockerignore

```
node_modules
.git
.env
*.md
Dockerfile
.dockerignore
```

### 4. Set Non-Root User (Security)

```dockerfile
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

### 5. Use Specific Tags

```dockerfile
# Good - specific version
FROM node:20-alpine

# Bad - can change unexpectedly
FROM node:latest
```

---

## Framework Detection

When generating Dockerfiles, detect framework from:

| File | Framework |
|------|-----------|
| `next.config.js` | Next.js |
| `vite.config.*` | Vite |
| `vue.config.js` | Vue CLI |
| `angular.json` | Angular |
| `package.json` → react-scripts | Create React App |
| `requirements.txt` + `main.py` → fastapi | FastAPI |
| `requirements.txt` + `manage.py` | Django |
| `requirements.txt` + `app.py` → flask | Flask |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml` | Java/Maven |
| `build.gradle` | Java/Gradle |
| `*.csproj` | .NET |
