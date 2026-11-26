FROM python:3.11-slim

WORKDIR /srv/backend

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl xz-utils && rm -rf /var/lib/apt/lists/*

# Pinned Node.js runtime for the official FlagShark CLI (verified Phase 2).
# Exact upstream tarball + SHA256 from https://nodejs.org/dist/v22.23.4/SHASUMS256.txt
ARG NODE_VERSION=22.23.4
ARG NODE_SHA256=1805bcd35e6815559bd2eb97db438d3fdb0eb3a5e6a977b7c1badca76337e9ce
RUN curl -fsSLO "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
 && echo "${NODE_SHA256}  node-v${NODE_VERSION}-linux-x64.tar.xz" | sha256sum -c - \
 && tar -xJf "node-v${NODE_VERSION}-linux-x64.tar.xz" -C /usr/local --strip-components=1 \
 && rm "node-v${NODE_VERSION}-linux-x64.tar.xz" \
 && node --version && npm --version

# Pinned official FlagShark CLI. Build FAILS if the binary is not usable,
# so a missing/broken tool can never ship silently (build log shows version).
ARG FLAGSHARK_VERSION=2.8.0
RUN npm install -g "flagshark@${FLAGSHARK_VERSION}" \
 && flagshark --version \
 && git config --global --add safe.directory '*'

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && python -c "import importlib.metadata as m; v=m.version('polyglot-piranha'); assert v=='0.4.9', v; print('polyglot-piranha', v)"

COPY . ./

RUN mkdir -p /srv/backend/data /srv/workspaces

ENV DATABASE_URL=sqlite:///./data/feature_flags.db \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    FRONTEND_ORIGIN=http://localhost:5173 \
    WORKSPACE_DIR=/srv/workspaces

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
