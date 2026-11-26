"""Piranha subprocess entry point (invoked by piranha_service, never by users).

Usage: python3 piranha_runner.py <args.json> <out.json>

args.json: {language, paths_to_codebase, path_to_configurations,
            substitutions, dry_run}
out.json (written on success): {"summaries": [{path, rewrites, matches}]}
Any failure: traceback on stderr, nonzero exit. stdout stays clean.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    args_path, out_path = sys.argv[1], sys.argv[2]
    with open(args_path, encoding="utf-8") as f:
        args = json.load(f)
    try:
        from polyglot_piranha import PiranhaArguments, execute_piranha
    except ImportError as exc:
        print(f"polyglot-piranha is not installed: {exc}", file=sys.stderr)
        return 3
    try:
        pa = PiranhaArguments(
            language=args["language"],
            paths_to_codebase=args["paths_to_codebase"],
            path_to_configurations=args["path_to_configurations"],
            substitutions=args["substitutions"],
            dry_run=bool(args.get("dry_run", False)),
        )
        summaries = execute_piranha(pa)
    except Exception as exc:  # includes pyo3 panics surfaced as exceptions
        print(f"piranha execution failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    payload = {"summaries": [
        {"path": s.path,
         "rewrites": [{"rule": e.matched_rule,
                       "replacement": (e.replacement_string or "")[:2000],
                       "matched": ((e.p_match.matched_string if e.p_match else "") or "")[:2000]}
                      for e in (s.rewrites or [])],
         "matches": [{"rule": rule,
                      "captures": {k: (v[:500] if isinstance(v, str) else v)
                                   for k, v in ((m.matches if m else None) or {}).items()},
                      "matched": ((m.matched_string if m else "") or "")[:2000],
                      "row": (m.range.start_point.row
                              if m and m.range and m.range.start_point else None),
                      "column": (m.range.start_point.column
                                 if m and m.range and m.range.start_point else None)}
                     for rule, m in (s.matches or [])],
         "match_count": len(s.matches or [])}
        for s in (summaries or [])]}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
