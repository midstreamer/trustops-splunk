# TrustOps FastAPI backend — deploy to Railway, Render, Fly.io, etc.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY data/sample_alerts.json ./data/sample_alerts.json

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
ENV TRUSTOPS_STARTUP_SMOKE_TEST=skip

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
