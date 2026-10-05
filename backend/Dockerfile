FROM python:3.11-slim

WORKDIR /srv/backend

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN mkdir -p /srv/backend/data /srv/workspaces

ENV DATABASE_URL=sqlite:///./data/feature_flags.db \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    FRONTEND_ORIGIN=http://localhost:5173 \
    WORKSPACE_DIR=/srv/workspaces

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
