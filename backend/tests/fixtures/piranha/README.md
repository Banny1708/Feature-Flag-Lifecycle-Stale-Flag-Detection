# Piranha golden fixtures (RECORDED from real execution, never hand-written)

Generated 2026-10-25 from controlled runs of `polyglot-piranha==0.4.9`
against the `piranha-lab` fixture (boolean feature flags in Python +
TypeScript). `before/` is `git archive` of the fixture HEAD; `after/` is the
real worktree after `execute_piranha(..., dry_run=False)`; `expected.patch`
is the real `git diff`.

- `cases/py_true_*`: `FEATURE_NEW_UI` treated `True` (if/else elimination,
  boolean-expression simplification, import + definition deletion,
  multi-file, independent flags).
  NOTE: `after/case_nested.py` contains a REAL IndentationError produced by
  Piranha (nested-block dedent limitation) — the byte-equality test pins this
  behavior; `verify_python_syntax` is what turns it into FAILED, never SUCCESS.
- `cases/py_false_*`: `FEATURE_OLD_SEARCH` treated `False` (else-branch kept).
- `cases/ts_true_*`: `FEATURE_NEW_UI` treated `true` (braces kept as bare blocks).
- Leftover references are intentional and asserted: only the multi-name
  import line `from flags import FEATURE_NEW_UI, FEATURE_OLD_SEARCH`
  (py cases) survives — multi-name imports are a documented limitation.
- `python-rules.toml` / `ts-rules.toml` (+ edges): exact copies of the
  shipped `backend/piranha_configs/<lang>/` rule sets used in the runs.
- `metadata.json`: tool, version, language, flag, treated value per case.
