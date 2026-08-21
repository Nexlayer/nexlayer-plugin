# ============================================================================
# LARAVEL DOCKERFILE - Production with PHP-FPM + nginx
# ============================================================================
# Framework: Laravel
# Output: PHP-FPM with nginx
# Port: 8000
# ============================================================================

FROM php:8.3-fpm-alpine
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    nginx \
    supervisor \
    libpq-dev \
    libzip-dev \
    && docker-php-ext-install pdo pdo_pgsql pdo_mysql zip opcache

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Copy composer files and install dependencies
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist

# Copy application
COPY . .

# Finish composer install
RUN composer dump-autoload --optimize

# Set permissions
RUN chown -R www-data:www-data /app/storage /app/bootstrap/cache

# Configure nginx
RUN echo 'server { \
    listen 8000; \
    root /app/public; \
    index index.php; \
    location / { \
        try_files $uri $uri/ /index.php?$query_string; \
    } \
    location ~ \.php$ { \
        fastcgi_pass 127.0.0.1:9000; \
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name; \
        include fastcgi_params; \
    } \
}' > /etc/nginx/http.d/default.conf

# Configure supervisor
RUN echo '[supervisord] \
nodaemon=true \
[program:nginx] \
command=nginx -g "daemon off;" \
[program:php-fpm] \
command=php-fpm' > /etc/supervisord.conf

ENV APP_ENV=production

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
