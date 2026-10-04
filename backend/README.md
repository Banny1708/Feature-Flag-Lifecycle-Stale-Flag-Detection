# FFSD Backend (FastAPI + SQLite)

Backend for the Feature-Flag-Lifecycle-Stale-Flag-Detection frontend.
Responses use camelCase to match `src/types/index.ts` exactly.

## Quick start

```bash
cd backend
cp .env.example .env            # optional; defaults work locally
pip install -r requirements.txt
python -m alembic upgrade head  # create tables (SQLite file from DATABASE_URL)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for OpenAPI docs.

On startup the server creates tables (if missing) and seeds 5 repositories,
4 flags, 1 scan, evidence, code refs/paths, risk, 1 removal, verification and
1 report — the same dataset the frontend mocks show, so the UI works immediately.

## Full lifecycle workflow

```bash
# 1. register a local checkout (read-only git probe)
curl -X POST localhost:8000/api/repositories \
  -H 'Content-Type: application/json' \
  -d '{"name":"myrepo","local_path":"/abs/path/to/repo","default_branch":"main","language":"TypeScript"}'

# 2. run detection (git probe -> FlagShark or Regex-Fallback -> persist)
curl -X POST localhost:8000/api/scans \
  -H 'Content-Type: application/json' -d '{"repository_id":"<repo-id>"}'

# 3. inspect a flag
curl localhost:8000/api/flags/<flag-id>/evidence
curl localhost:8000/api/flags/<flag-id>/code-paths
curl -X POST localhost:8000/api/flags/<flag-id>/analyze   # recompute explainable risk

# 4. user-confirmed removal (safety branch + Piranha + tests + verification)
curl -X POST localhost:8000/api/flags/<flag-id>/remove \
  -H 'Content-Type: application/json' \
  -d '{"flag_id":"<flag-id>","target_branch":"main","tool_target":"Piranha"}'
```

## Tool integrations (real, never faked)

| Tool | Behavior when missing |
|---|---|
| FlagShark (`FLAGS_HARK_BIN`) | Scan falls back to an honest local reference scan labelled `Regex-Fallback`; if that finds nothing the scan is `failed` with "FlagShark is not installed" |
| Piranha (`PIRANHA_BIN`) | `POST .../remove` returns 500 `Piranha UNAVAILABLE`; nothing is modified |
| git | Git evidence fields return `"UNAVAILABLE"`; removal is refused (safety branch required) |
| Maven/JaCoCo | Test command auto-detected (`pom.xml` -> `mvn -q test`, else npm/pytest/go); coverage stays `"unavailable"` unless a real `jacoco.xml` is parsed |

Removal verdicts are `SUCCESS` / `FAILED` / `UNVERIFIED` — never SUCCESS on Piranha
exit code alone: flag references must be gone AND tests must pass.

## Config (.env)

DATABASE_URL, BACKEND_HOST, BACKEND_PORT, FRONTEND_ORIGIN (CORS for Vite, default
http://localhost:5173), WORKSPACE_DIR, FLAGS_HARK_BIN, PIRANHA_BIN, GIT_BIN,
MVN_BIN, SCAN/PIRANHA/TEST_TIMEOUT_SEC. See `.env.example`.

## Tests

```bash
python -m pytest tests/ -q
```

Tests use a temp SQLite DB and assert honest tool-missing behavior (no faked successes).
