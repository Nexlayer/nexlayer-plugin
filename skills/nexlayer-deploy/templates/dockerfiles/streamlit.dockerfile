# ============================================================================
# STREAMLIT DOCKERFILE
# ============================================================================
# Framework: Streamlit
# Output: Streamlit server
# Port: 8501
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
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

EXPOSE 8501

# Find and run Streamlit app
CMD ["sh", "-c", "\
  if [ -f app.py ]; then \
    streamlit run app.py --server.port=8501 --server.address=0.0.0.0; \
  elif [ -f main.py ]; then \
    streamlit run main.py --server.port=8501 --server.address=0.0.0.0; \
  elif [ -f streamlit_app.py ]; then \
    streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0; \
  else \
    streamlit run $(ls *.py | head -1) --server.port=8501 --server.address=0.0.0.0; \
  fi"]
