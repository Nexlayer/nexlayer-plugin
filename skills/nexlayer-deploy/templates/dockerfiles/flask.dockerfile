# ============================================================================
# FLASK DOCKERFILE - Production with gunicorn
# ============================================================================
# Framework: Flask
# Output: WSGI server with gunicorn
# Port: 5000
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV PORT=5000

EXPOSE 5000

# Find and run the Flask app
CMD ["sh", "-c", "\
  if [ -f app.py ]; then \
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 2; \
  elif [ -f main.py ]; then \
    gunicorn main:app --bind 0.0.0.0:$PORT --workers 2; \
  elif [ -f application.py ]; then \
    gunicorn application:app --bind 0.0.0.0:$PORT --workers 2; \
  elif [ -f wsgi.py ]; then \
    gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2; \
  else \
    echo 'No Flask app found' && exit 1; \
  fi"]
