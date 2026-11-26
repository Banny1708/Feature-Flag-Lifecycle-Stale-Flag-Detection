# FlagOps Piranha rule configurations (VERIFIED against real runs)

These TOML rule sets drive Polyglot Piranha `0.4.9` for boolean feature-flag
cleanup. Every rule/edge below was verified by executing the real tool against
controlled fixtures; no rule here is guessed.

Pattern: a seed rule rewrites flag-identifier reads in `if` conditions to the
`@treated` boolean literal; chained cleanup rules then simplify
`if True:`/`if False:` blocks, boolean expressions, single-name imports
(multi-name imports are preserved), and flag definitions. The seed never
matches attribute parts (`flags.FEATURE_X`), subscript uses, aliased imports,
or import statements (themselves handled by dedicated rules where safe) —
all verified by probe tests.

- `python/`: `True`/`False` literals, tree-sitter python queries.
  Verified: if/else elimination (single nesting level), if-without-else
  deletion on false, boolean-expression simplification, multi-file,
  independent flags, LaunchDarkly `variation("FLAG", ...)` incl. chained
  `ldclient.get().variation(...)`.
- `typescript/`: `true`/`false` literals, tree-sitter typescript queries.
  Shared rules also cover `tsx` (verified on `if` statements). if/else
  elimination keeps braces (`{ ... }` bare blocks — valid TS/JS).
  Verified methods: variation, boolVariation, stringVariation,
  numberVariation, jsonVariation.
- `providers/launchdarkly/`: match-only DETECTION rules (no rewrites) used
  by the ProviderAST inventory layer.

KNOWN LIMITATIONS (all verified; all fail safe via verification, never fake):
- Nested-`if` consequence blocks in Python rewrite with broken indentation
  (IndentationError); verification catches it and the operation FAILS.
- Multi-name imports (`from m import A, B`) and `*Detail` SDK variants are
  left intact; leftover references fail verification honestly.
- Conditional reads outside `if` conditions (e.g. `y = f(...)`), ternaries,
  and computed/env-derived keys are not matched (NO_CHANGES).

Rules use only `flag_name` + `treated` holes (always supplied by the adapter;
missing holes crash Piranha, so the adapter validates first). Scope
`ParentIterative` for boolean chains; group-to-group edges only (query-less
dummy junction rules break chaining via TOML loading — verified).
