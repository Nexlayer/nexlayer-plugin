# ============================================================================
# FASTAPI DOCKERFILE - Production with uvicorn
# ============================================================================
# Framework: FastAPI
# Output: ASGI server with uvicorn
# Port: 8000
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

EXPOSE 8000

# Find and run the FastAPI app
# Looks for: main:app, app:app, api:app, src.main:app
CMD ["sh", "-c", "\
  if [ -f main.py ]; then \
    uvicorn main:app --host 0.0.0.0 --port $PORT; \
  elif [ -f app.py ]; then \
    uvicorn app:app --host 0.0.0.0 --port $PORT; \
  elif [ -f api.py ]; then \
    uvicorn api:app --host 0.0.0.0 --port $PORT; \
  elif [ -f src/main.py ]; then \
    uvicorn src.main:app --host 0.0.0.0 --port $PORT; \
  elif [ -f app/main.py ]; then \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT; \
  else \
    echo 'No FastAPI app found' && exit 1; \
  fi"]
