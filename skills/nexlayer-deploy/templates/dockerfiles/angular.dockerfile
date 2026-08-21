# ============================================================================
# ANGULAR DOCKERFILE - Production Build
# ============================================================================
# Framework: Angular
# Output: Static files served by nginx
# Port: 80
# ============================================================================

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

# Production stage
FROM nginx:alpine

# Find and copy the build output (Angular puts it in dist/project-name/)
COPY --from=builder /app/dist/*/ /usr/share/nginx/html/

RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
