---
name: qa
description: Run the full quality gate for this repo (ruff lint/format, mypy, pytest with coverage) exactly as CI does. Use before committing, when asked to "run the checks/tests/QA", or to verify a change didn't break anything.
---

# Quality gate

Run all checks the CI pipeline runs, in this order (fail fast on the cheap
ones first). All commands run through `uv` from the repo root:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy --no-warn-unused-ignores src tests
uv run pytest --cov tests/
```

Equivalent one-shot for the lint half (what the lint workflow runs):

```sh
uv run pre-commit run --all-files
```

## Notes

- If the environment is missing or stale, run `uv sync --extra dev` first.
- `ruff format --check` only reports; drop `--check` to actually reformat.
- Fixable lint findings: `uv run ruff check --fix .` (only UP, I, D, RUF022
  are configured as fixable).
- CI tests on Python 3.13 **and** 3.14. If a change touches
  version-sensitive behavior, also run
  `uv run --python 3.14 pytest tests/` when a 3.14 interpreter is available.
- Coverage measures the `jsonsubschema` package with branch coverage
  (see `[tool.coverage.run]` in pyproject.toml). For an HTML report:
  `uv run pytest --cov --cov-report=html tests/` (output in `htmlcov/`,
  which is gitignored).
- Do not fix McCabe-complexity findings (C901) with `noqa` — extract helper
  functions instead; see AGENTS.md.
