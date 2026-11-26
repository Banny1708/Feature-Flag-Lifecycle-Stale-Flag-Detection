# Project Review Report — Feature Flag Lifecycle With Stale Flag Detection

**Date:** 2026-10-12 · **Scope:** entire repository (frontend, backend, database, Docker, tests)
**Method:** live inspection of the running Docker stack + source reads + 45-check API matrix +
fixture-driven workflow runs + build/test executions. No finding below is assumed; every
behavioral claim was exercised against the running system unless marked otherwise.
**Working tree state at audit time:** 3 commits on `main`, ~58 files of reviewed work uncommitted.

---

## 1. What this project is

A full-stack feature-flag governance system. The React UI operates a FastAPI backend that
registers repositories, scans them for flags, persists lifecycle/detection/risk/removal/
evidence records in PostgreSQL, and performs guarded removals with verification and rollback.
All UI data comes from the backend; all backend writes land in the database; all tool
interactions are real subprocess calls with honest unavailable-tool handling.

```
Browser (:3000 nginx SPA) ──REST/JSON──▶ FastAPI (:8000) ──SQLAlchemy──▶ PostgreSQL 16 (:5432)
        │                                        │  ▲
        │ loading / empty / error states         │  │ subprocess (arg arrays, timeouts)
        │ (no mock fallback anywhere)            ▼  ▼
        │                                   git (real) · FlagShark (absent→honest fallback)
        │                                   Piranha (absent→honest refusal) · mvn/npm/pytest · JaCoCo
        └───────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Frontend — what was built

**Stack:** React 18 + TypeScript (strict, `tsc` 0 errors) + Vite + React Router v6 + TailwindCSS + Lucide.
**Verified:** `vite build` succeeds (1620 modules); all 9 routes serve HTTP 200 (incl. SPA fallback);
production bundle contains zero mock references; no `alert()`, no `localStorage`, no TODOs.

| Page (`src/pages/`) | Live APIs consumed | States |
|---|---|---|
| Dashboard | flags, repos, scans, removals, tools-status | loading / error+retry / empty stale table |
| Feature Flags | flags, repos (real JSON export) | loading / error / empty + no-match |
| Stale Flags | stale-flags, risk-assessments, settings, dry-run, remove | loading / error / empty + per-op errors |
| Code Analysis | flags, references, code-paths | loading / error / empty |
| Repositories | repos, scans, connect | loading / error / empty + inline op errors |
| Removal Operations | removals, stale-flags, dry-run, remove, rollback | loading / error / empty + op errors |
| Verification | verifications (status-reflecting badges) | loading / error / empty |
| Reports | reports, evidence, generate, download | loading / error / empty + action errors |
| Settings | settings GET/PUT (thresholds + integrations) | loading / error / save error |
| Sidebar / Topbar | repos/flags/removals counts; real scan-all loop | failure banner (red) vs success (green) |

**Removed during cleanup:** `src/data/` (8 mock files, ~940 lines), 6 fake `alert()` mutations,
fake scan timer + hardcoded banner, hardcoded dashboard stats/badges, fake token default,
hardcoded removal-flag options. Minimal type updates only where the backend legitimately
returns more (`RemovalStatus` += PENDING/RUNNING/SUCCESS/FAILED/ROLLED_BACK;
`RiskAssessment.recommendation/riskLevel?`; `RemovalOperation.operationType/safetyBranch/
verificationStatus?`).

---

## 3. Backend — what was built (`backend/app/`)

FastAPI app (v2.0.0, `/docs` live), **48 endpoints** across 9 routers. Every frontend call
shape maps to a route (exhaustive cross-check); a 45-case matrix (valid/invalid/malformed/
404/409/422/400/500 + error-shape + CORS preflight) passes **45/45**.

- `config.py` — env-first settings; Postgres DSN preferred, SQLite dev fallback; no secrets in code.
- `database.py` — dual-dialect engine, `pool_pre_ping`, `wait_for_db` (30×2s), `get_db` DI.
- `models/` — 20 tables (see §4); ORM never leaks (Pydantic camelCase schemas + mappers).
- `services/` — `git` (read-only evidence, safety branches), `flagshark` (binary probe →
  CLI shapes → JSON normalize → labelled Regex-Fallback → honest `failed`), `piranha`
  (safety branch → execution → diff/`numstat` capture → honest UNAVAILABLE refusal),
  `test` (mvn/npm/pytest/go autodetect + JaCoCo XML parse, `unavailable` otherwise),
  `codepath` (real file reads; coverage never invented), `evidence` (git/scan/FS only),
  `detection` (deterministic 0–100 multi-signal scoring, documented), `risk`
  (rule-based + SAFE/REVIEW/DO_NOT_REMOVE mapping), `lifecycle` (validated state machine),
  `audit` (append-only), `seed` (idempotent `[DEMO]` dataset).
- `routers/` — health, projects, repositories, scans, flags, analyze, analysis_runs,
  removals, reports, settings. Global handler returns structured JSON 500s (no tracebacks).
- No authentication (documented as out of scope); no structured logging (uvicorn only);
  `main.py` lifespan assignment is functional but non-idiomatic.

**Bugs found by testing and fixed:** (1) repo-less flag creation 500'd (FK) → nullable FK +
migration + 422 on unknown repo; (2) analysis evidence lacked `analysis_run_id` linkage →
linked; (3) unhandled exceptions returned plain-text 500s → JSON handler.

---

## 4. Database — what was built

**PostgreSQL 16 primary** (compose volume `pgdata`; verified persisting across restarts),
SQLite file retained for zero-setup dev/tests. One Alembic chain (4 migrations) serves both
dialects and upgrades clean installs from zero (verified on scratch PG).

21 relations live (`\dt` confirmed): `projects`, `repositories`, `feature_flags` (+lifecycle
columns), `flag_evaluations`, `scans`, `scan_findings`, `code_references`, `code_paths`,
`analysis_runs`, `detection_results`, `untested_paths`, `risk_assessments`, `risk_factors`,
`removal_operations`, `test_runs`, `verification_results`, `evidence_records`, `audit_logs`,
`reports`, `system_settings` (+ `alembic_version`). FK/NOT-NULL enforcement proven by
rejected inserts; named constraints; batch mode for SQLite. `audit_logs` deliberately
FK-free (append-only). Local dev DB holds some manual test residue — reseed if a pristine
demo is needed. Verified quirk trapped in code: raw-FK same-flush children need
parent-first flushes on Postgres (regression-covered by `test_postgres.py`).

**Lifecycle machine enforced:** ACTIVE→ROLLOUT→CONCLUDED→STALE_CANDIDATE→RISK_REVIEW→
REMOVAL_PENDING→REMOVED (+recovery edge), invalid jumps → 422, UI `status` synced.

---

## 5. Workflow evidence (live fixture runs, not simulations)

Register (201) → scan finds `FLAG` at exact file:line with real commit hash → git evidence
(real branch/commit/clean) → `FULL_ANALYSIS` COMPLETED → verdicts with reason strings
(fresh flag correctly `ACTIVE/0`, never falsely stale) → code paths with real conditions,
coverage `unavailable` → untested-path rows with proof-based reasons → risk with scored
factors → dry-run plans real files with repo untouched → lifecycle walk → tool-absent
removal refused (500 + `FAILED` op + `REMOVAL_FAILED` audit + safety branch preserved) →
per-flag history and global audit readable. Empty repos yield `failed` scans, never fake flags.

---

## 6. Docker / infra — what was built and verified

`postgres` (healthcheck, `pgdata`), `ffsd-backend` (waits healthy, migrates, seeds;
also `wait_for_db`), `ffsd-frontend` (nginx SPA, healthcheck). CORS correct for :3000.
Repaired during testing: backend had lost its compose network (down/up reconciled).
Backend image ships `git` only — FlagShark/Piranha/Maven absent by environment, not by code.

---

## 7. Tests — what exists and their results

- Backend pytest: **17/17** (health, CRUD, lifecycle valid/invalid, evaluations, REJECTED vs
  STALE detection, untested paths, risk recommendation, dry-run purity, refusal paths,
  real-git rollback restore, tool-missing handling) + 2 Postgres-gated (FK/seed/migration).
- No frontend unit tests. No browser available on this machine, so console-error
  observation was approximated via `tsc` + bundle + route + code-path verification.

---

## 8. Capstone requirement verdicts

| Requirement | Verdict | Basis |
|---|---|---|
| Lifecycle management | **PASS** | state machine, 422s, history, 15/15 live checks |
| Stale detection | **PASS** | deterministic engine, stored explainable verdicts |
| Code-path analysis | **PASS** | real reads, honest coverage |
| Risk assessment | **PASS** | traceable factors + persisted recommendations |
| Safe removal | **PARTIAL** | dry-run/guards/safety/rollback real; Piranha execution never demonstrated (binary absent) |
| Verification | **PARTIAL** | pipeline + refusals real; live records await a completed removal |
| Evidence/reproducibility | **PASS** | per-operation evidence, audit trail, migrations, seed, docs |
| Complete frontend | **PASS** | 9 live pages, full state coverage, zero mocks (no browser-console check possible here) |
| Complete backend | **PASS** | 48 endpoints, 45/45 matrix |
| Persistent database | **PASS** | PG+volume, restart-proof, clean-install proven |
| Integrated workflow | **PARTIAL** | live end-to-end up to the tool-execution boundary |

---

## 9. Outstanding items (in priority order)

1. **Install FlagShark/Piranha (/Maven) into the backend image or document as prerequisites,**
   then execute one fixture scan + removal end-to-end. No code changes expected; closes the
   two PARTIALs. (`backend/Dockerfile`, docs)
2. Commit the ~58 reviewed files (demo runs from working tree).
3. Decide demo-DB contents: purge test traces (`e2e-*`, probes) or keep as evidence; reseed
   local SQLite if pristine demo desired.
4. Optional: frontend smoke tests, structured logging, auth (only if the rubric demands).
5. `VITE_API_URL` is baked at build time — fine for local demo; external hosting needs a
   build-arg or runtime config.

**Bottom line:** a genuine, database-backed, API-driven working system — demonstrable today
for everything except tool-executed removal, where it provably refuses to fake success.
