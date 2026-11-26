# FlagShark golden fixture (RECORDED, not hand-written)

Source: actual `flagshark scan --format json` invocation, 2026-10-24.

- Tool: official CLI `flagshark@2.8.0` (npm, MIT), `flagshark v2.8.0`
- Command (cwd = fixture repo): `flagshark scan --format json`
- Exit code: 1 (stale flags found — expected)
- Fixture repo: TypeScript (`launchdarkly-node-server-sdk`: `variation`,
  `boolVariation`, wrapper forwarding) + Python (`ldclient`), one test-only
  flag, git history with old (2025-06) and fresh (2026-10-24) commits

What the output proves about the v2.8.0 schema:

- Top-level: `version, totalFlags, staleFlags, errorCount, parseErrorCount,
  excludedPermanent, permanentByPlatform, healthScore, detectedProviders,
  languages, flags[], scanDuration, links`
- `flags[]` contains STALE flags only: `totalFlags=4` but 3 entries
  (the fresh `FRESH_ROLLOUT_2026` is counted, not listed)
- One entry per unique flag (first location), not per occurrence
- `file` is an ABSOLUTE path; `line` is an int
- `confidence` is a STRING tier (`high`/`medium`/`low`), not a number
- `signals[]` entries are `{type, severity, description}`; `age` is a human
  string (`"1 year ago"`) or null — never a day count
- No AST node types, no numeric confidence, no `is_stale: false` entries

Paths in this file are verbatim (`/repo/...` was the scan root). Tests load
this file and normalize against `Path("/repo")` using pure path math.
