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

On startup the server creates tables (if missing). No demo data is inserted:
a fresh database stays empty until real repositories are connected and scanned.
(The automated tests use isolated fixtures in `tests/fixtures.py`.)

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
| FlagShark (`FLAGS_HARK_BIN`, official `flagshark@2.8.0` pinned in Dockerfile) | `flagshark scan --format json` (cwd = repo; exits 0/1/2); stale-only `flags[]` normalized with real language/provider/signals/age; `ast_node_type` honestly `"Unknown"`; failures/timeouts fall back to the labelled `Regex-Fallback`; no binary + no references → scan `failed` with "FlagShark is not installed" |
| ProviderAST (LaunchDarkly, same pinned Piranha lib, match-only rules) | Supplement to FlagShark, never a replacement: import-gated match scans for literal-key `variation`/`boolVariation`/`stringVariation`/`numberVariation`/`jsonVariation` calls (py/ts). Findings are inventory with source `ProviderAST(<provider>)`, never stale verdicts; detail-variants, computed and env-derived keys are excluded by construction |
| Piranha (`polyglot-piranha==0.4.9`, pinned in requirements/Dockerfile) | Verified adapter: Python-API execution in an isolated subprocess (`piranha_runner.py`), shipped rule configs for `python`/`typescript`/`tsx` only (incl. LaunchDarkly `variation*` call seeds). Unsupported languages/config problems fail closed (`UNSUPPORTED`, never a guessed cleanup). Dry-run is mutation-free and purity-verified; approved cleanup captures the real unified diff, runs tests + syntax check + FlagShark re-scan, and rolls back via safety-branch reset. |
| git | Git evidence fields return `"UNAVAILABLE"`; removal is refused (safety branch required) |
| Maven/JaCoCo | Test command auto-detected (root `pom.xml` → `mvn -q test`, else npm-with-test-script/pytest/go; subdirectories scanned to depth 3, monorepo-aware). Missing tool with markers present → explicit `TOOL_UNAVAILABLE`, never a pass. Coverage stays `"unavailable"` unless a real `jacoco.xml` is parsed (no thresholds) |

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
