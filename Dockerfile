FROM python:3.11-slim
WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY server ./server
COPY web ./web
ENV STATE_DIR=/data/state WEB_DATA_ROOT=/data/web
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
