# ============================================================================
# DJANGO DOCKERFILE - Production with gunicorn
# ============================================================================
# Framework: Django
# Output: WSGI server with gunicorn
# Port: 8000
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

EXPOSE 8000

# Find the Django project name and run gunicorn
# Looks for wsgi.py in any subdirectory
CMD ["sh", "-c", "\
  PROJECT=$(find . -name 'wsgi.py' -type f | head -1 | xargs dirname | xargs basename); \
  if [ -n \"$PROJECT\" ]; then \
    gunicorn ${PROJECT}.wsgi:application --bind 0.0.0.0:$PORT --workers 2; \
  else \
    echo 'No Django wsgi.py found' && exit 1; \
  fi"]
