---
name: debug-subschema
description: Investigate why is_subschema returns an unexpected result or raises, by inspecting the canonicalization/simplification pipeline and per-type checkers. Use when debugging a wrong/surprising subtype verdict, an "unsupported" exception, or when adding support for a new schema feature.
---

# Debugging a subschema check

## Reproduce first

Write a minimal pytest-style repro with inline schema dicts (no JSON files —
`*.json` is gitignored here):

```python
from jsonsubschema import is_subschema
s1 = {"type": "string", "minLength": 5}
s2 = {"type": "string"}
print(is_subschema(s1, s2))
```

Run it with `uv run python <script>` (or `uv run python -c "..."`). The CLI
alternative for existing files: `uv run jsonsubschema lhs.json rhs.json`.

## Inspect the pipeline stage by stage

The result is produced in three stages; find out which one loses or distorts
information:

```python
from jsonsubschema import canonicalize_schema, set_debug
from jsonsubschema._canonicalization import simplify_schema_and_embed_checkers

set_debug(True)  # prints intermediate forms during API calls

c = canonicalize_schema(s1)          # stage 1: canonical form (plain dict)
e = simplify_schema_and_embed_checkers(c)  # stage 2: simplified, JSONschema instance
print(type(e), dict(e))              # JSONschema subclasses dict
```

- Stage 1+2 live in `src/jsonsubschema/_canonicalization.py`.
- Stage 3 (the actual `<:` decision) lives in `src/jsonsubschema/_checkers.py`:
  each JSON type has a `JSON<type>` class with `_is_subtype`, `_meet`, `_join`
  hooks; dispatch happens in the `JSONschema` base class.

## Things to know while reading `_checkers.py`

- `JSONschema` objects are dicts with behavior; `JSONbot` (uninhabited /
  bottom) and `JSONtop` (anything / top) are special. `obj == False` /
  `obj == True` comparisons are **intentional** (overridden `__eq__`) —
  don't rewrite them.
- Numeric ranges use the `portion` interval library; string patterns are
  compared as DFAs via `greenery.parse`. Wrong string verdicts are often a
  regex-translation issue in `_utils.py` (e.g. length bounds → regex).
- Uninhabited detection runs on every construction via `UninhabitedMeta`;
  `set_warn_uninhabited(True)` makes it warn.

## Unsupported cases

`RecursionError` during canonicalization is converted to
`UnsupportedRecursiveRef`. Negated objects/arrays raise
`UnsupportedNegatedObject`/`UnsupportedNegatedArray`. If a check hits one of
these, the correct fix is usually to extend support or improve the error —
never to guess a `True`/`False` verdict.

## When you find the bug

Add a regression test in the matching `tests/test_<type>.py` file (plain
`test_*` function, assert both directions), and check whether upstream
[IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) has the same bug —
if so, note it in the PR description.
