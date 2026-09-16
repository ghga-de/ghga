---
name: sync-upstream
description: Compare this fork against IBM/jsonsubschema upstream and port over relevant fixes or check for divergence. Use when asked to sync with upstream, port an upstream commit/PR, or check whether an upstream bug exists here.
---

# Syncing with upstream IBM/jsonsubschema

This repo is a fork of https://github.com/ibm/jsonsubschema, based on its
version 0.0.8 (released June 2026), with deliberate divergences (see
"Changes made by GHGA" in README.md).

## Fetching upstream

```sh
git remote add upstream https://github.com/ibm/jsonsubschema.git 2>/dev/null
git fetch upstream
git log --oneline upstream/master -- jsonsubschema/   # upstream layout is flat, not src/
```

Or inspect specific commits/PRs without a remote:
`gh api repos/ibm/jsonsubschema/commits --jq '.[].commit.message'` or
`gh pr view <n> --repo ibm/jsonsubschema --json title,body,files`.

## Translation table (upstream → this fork)

Upstream code does NOT apply verbatim. Translate:

| Upstream | Here |
|---|---|
| `jsonsubschema/<file>.py` | `src/jsonsubschema/<file>.py` |
| `isSubschema`, `isEquivalent` | `is_subschema`, `is_equivalent` |
| `meet`, `join` (API level) | `meet_schemas`, `join_schemas` |
| `canonicalizeSchema` | `canonicalize_schema` |
| `set_debug`/camelCase config setters | see `config.py` for actual names |
| unittest `TestCase` classes | plain pytest `test_*` functions |
| Python 3.8+ compatibility code | Python 3.13+ idioms only |

Internal helper names in `_checkers.py`/`_canonicalization.py`/`_utils.py`
were also PEP 8-ified — grep for the equivalent snake_case name rather than
assuming the upstream name exists.

## Known deliberate divergences (do NOT "fix back")

- Empty `enum` is treated as an uninhabited schema here (upstream may differ).
- Packaging: `pyproject.toml` + `uv`, `src/` layout, PyPI name
  `ghga-jsonsubschema`.
- Stricter ruff/mypy configuration; upstream code often needs docstrings,
  complexity reduction, and naming fixes before it passes `uv run
  pre-commit run --all-files` here.

## Porting checklist

1. Identify the upstream commit(s); read the diff and the linked issue.
2. Re-apply the change by hand in the translated form (cherry-picks won't
   apply cleanly across the rename/layout changes).
3. Port or write the accompanying tests as pytest functions in the matching
   `tests/test_*.py` file.
4. Run the full quality gate (see the `qa` skill).
5. If the change alters user-visible behavior, update README.md's
   "Changes made by GHGA" section and mention the upstream commit/PR in the
   commit message.
