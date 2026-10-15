FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git nodejs npm ca-certificates \
    && npm install -g netlify-cli@17 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY server ./server
COPY scripts/lib ./scripts/lib
COPY web ./web
ENV STATE_DIR=/data/state WEB_DATA_ROOT=/data/web
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
