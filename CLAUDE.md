# Claude Code Instructions

Strictly follow the rules in ./AGENTS.md

Project guidance in the [README](README.md) and relevant files in [docs/](docs/) is also
authoritative for both human developers and agents. This file is intentionally small.

For work under `frontend/data-portal/`, its own
[AGENTS.md](frontend/data-portal/AGENTS.md) and
[CLAUDE.md](frontend/data-portal/CLAUDE.md) apply in addition.

When making changes:

- Prefer minimal diffs
- Explain non-obvious refactors
- Run the smallest relevant validation before suggesting changes (see the execution
  policy in [AGENTS.md](AGENTS.md))
