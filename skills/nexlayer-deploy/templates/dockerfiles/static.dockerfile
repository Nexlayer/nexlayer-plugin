# ============================================================================
# STATIC SITE DOCKERFILE - HTML/CSS/JS
# ============================================================================
# Framework: Static HTML, Hugo, Jekyll output, etc.
# Output: nginx serving static files
# Port: 80
# ============================================================================

FROM nginx:alpine

# Copy static files
# Supports common static site structures
COPY . /usr/share/nginx/html/

# Remove any files that shouldn't be served
RUN rm -f /usr/share/nginx/html/Dockerfile \
    /usr/share/nginx/html/docker-compose.yml \
    /usr/share/nginx/html/.git* \
    /usr/share/nginx/html/README.md 2>/dev/null || true

# SPA + static file configuration
RUN echo 'server { \
    listen 80; \
    listen [::]:80; \
    root /usr/share/nginx/html; \
    index index.html index.htm; \
    \
    location / { \
        try_files $uri $uri/ $uri.html /index.html; \
    } \
    \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|webp|avif)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
    \
    location ~* \.(html)$ { \
        expires 1h; \
        add_header Cache-Control "public, must-revalidate"; \
    } \
    \
    gzip on; \
    gzip_vary on; \
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml; \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
