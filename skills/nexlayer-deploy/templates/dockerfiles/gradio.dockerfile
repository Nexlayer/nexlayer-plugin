# ============================================================================
# GRADIO DOCKERFILE
# ============================================================================
# Framework: Gradio
# Output: Gradio server
# Port: 7860
# ============================================================================

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (for audio/image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

EXPOSE 7860

CMD ["sh", "-c", "\
  if [ -f app.py ]; then python app.py; \
  elif [ -f main.py ]; then python main.py; \
  elif [ -f gradio_app.py ]; then python gradio_app.py; \
  else python $(ls *.py | head -1); fi"]
