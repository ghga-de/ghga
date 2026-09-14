# Claude Code Instructions

@AGENTS.md

@docs/style.md

@docs/conventions.md

The project default output style is **GHGA Dev**
(`.claude/output-styles/ghga-dev.md`), which keeps the dev team house style steady
across long sessions. To use another one, set `outputStyle` in
`.claude/settings.local.json`; your user settings do not override it.
[awesome-claude-output-styles](https://github.com/smixs/awesome-claude-output-styles)
has ready-made styles to try; its "No Slop" style comes closest to ours. Its
[style-maker](https://github.com/smixs/awesome-claude-output-styles#make-your-own-style-maker)
skill builds a style from a short interview; it activates the result in your user
settings, so set it in `.claude/settings.local.json` instead.

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
