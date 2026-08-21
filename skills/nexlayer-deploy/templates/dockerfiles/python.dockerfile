# ============================================================================
# PYTHON DOCKERFILE - Generic Python Application
# ============================================================================
# Framework: Any Python application
# Output: Python runtime
# Port: 8000
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Handle different dependency files
COPY requirements*.txt pyproject.toml* setup.py* ./

# Install dependencies
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    elif [ -f pyproject.toml ]; then \
      pip install --no-cache-dir .; \
    elif [ -f setup.py ]; then \
      pip install --no-cache-dir .; \
    fi

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

# Auto-detect entry point
CMD ["sh", "-c", "\
  if [ -f main.py ]; then \
    python main.py; \
  elif [ -f app.py ]; then \
    python app.py; \
  elif [ -f run.py ]; then \
    python run.py; \
  elif [ -f server.py ]; then \
    python server.py; \
  elif [ -f src/main.py ]; then \
    python src/main.py; \
  elif [ -f -m ]; then \
    python -m $(basename $(pwd)); \
  else \
    echo 'No Python entry point found' && exit 1; \
  fi"]
