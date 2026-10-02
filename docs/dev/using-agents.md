# Using agents

How to work with coding agents in this repo, for the dev using them.
Whoever changes the instruction files themselves reads [agent-instructions.md](../agent-instructions.md) instead.
If you are new to the repo, read [getting-started.md](getting-started.md) first.

## What the repo sets up

- **Instructions:** `AGENTS.md` at the root and one per area; an agent reads the root file at the start and an area's file once it works there ([agent-instructions.md](../agent-instructions.md#areas)).
  There is no `CLAUDE.md`: Claude Code reads `AGENTS.md` itself, from v2.1.277 on.
- **Skills:** task procedures in `.agents/skills/`, listed with where each applies in the [skill catalogue](../agent-skills.md); `/skills` in Claude Code lists the ones your session can use.
- **Hooks:** in [`.claude/settings.json`](../../.claude/settings.json), a check at session start that you run in the dev container, and guards that stop edits to generated files and `uv` on the host.
- **Permissions:** the same file allows the read-only `gh` commands, asks before creating or commenting on a PR, and denies merges, releases, force pushes and reading `.env` files.
- **MCP:** only the data portal has servers, in [`frontend/data-portal/.mcp.json`](../../frontend/data-portal/.mcp.json); a session started at the repo root does not load them.
- **Output style:** Claude Code sessions default to **GHGA Dev** ([`.claude/output-styles/ghga-dev.md`](../../.claude/output-styles/ghga-dev.md)), which keeps replies short and plain.

## Personal setup

Personal instructions go in one of these, never in a committed file:

- **`~/.claude/CLAUDE.md`** loads in every project and lives on the `ghga-claude` volume, so it survives a container rebuild.
- **`.claude/rules/personal.local.md`**, or any `*.local.md` there, loads for this repo only and is gitignored.
  It exists only in the checkout or worktree you create it in.
- **`CLAUDE.local.md`** works only if you set **Project instructions** to `claude-md-and-agents-md` in `/config`.
  Without that setting, Claude Code finds the `CLAUDE.local.md`, takes it as the project's instructions and skips every `AGENTS.md`.
  A `CLAUDE.local.md` in the main checkout also sits above every worktree in `.claude/worktrees/`, so it has the same effect there.

Personal settings go in `.claude/settings.local.json`, which is gitignored.
To use another output style, set `outputStyle` there; your user settings do not override the project's default.

What you learn goes where the people who need it will find it:

| Knowledge | Where |
|---|---|
| a rule the team follows | a PR to `docs/` or an `AGENTS.md` |
| a procedure for one task | a skill |
| your own preference ("answer in German") | your personal instructions, or Claude's auto memory |
| a fact from a session that others need | a PR to `docs/` or an `AGENTS.md`, not memory |

Auto memory is per machine and per tool, and nobody reviews it; in the dev container it lives on the `ghga-claude` volume.
Do not use tools such as claude-mem on this repo: they record every tool output, and some sync it to a cloud.

## Parallel work

`just wt <branch>` creates a git worktree for a second agent session or a quick fix next to your feature branch.
It cuts the branch from `origin/dev`, or from the base you pass as the second argument, puts the worktree in `.claude/worktrees/` and syncs its `.venv`, so `just test` works there at once.
`just wt-rm <name>` removes the worktree and keeps the branch.

- **Open it** in its own VS Code window with *File → Open Folder…* and the worktree's path; the dialog shows the container's file system, so the window stays in the same container.
  Or `cd` into it in a terminal and run `claude`.
- **One at a time** runs the demo or the test bed, since all worktrees share one kind cluster and the host's ports.
- **A locked worktree:** Claude Code locks the worktrees of its background sessions, and `just wt-rm` fails on them until you run `git worktree unlock <path>`.
- **After a squash merge,** delete the branch with `git branch -D`; `-d` refuses it.

## Checking your setup

- At the start of a session, Claude Code prints `no CLAUDE.md found; AGENTS.md loaded: …`.
  If it does not, a `CLAUDE.md` or `CLAUDE.local.md` sits in or above your working directory.
- `/memory` lists the instruction files the session has loaded.
- `/doctor prompt-audit` checks the instruction files, rules, skills and output styles for stale or contradicting content, yours and the repo's.

## Changing the shared setup

A rule is a PR to an `AGENTS.md` or `docs/`, and a skill a PR to `.agents/skills/`; [agent-instructions.md](../agent-instructions.md) says which file a change belongs in.
A change to a root skill with an eval suite gets a pass, `just skill-eval <name>`, quoted in the PR ([agent-instructions.md](../agent-instructions.md#admitting-a-skill)).
It runs about 45 sessions on your own Claude credential in 15 to 20 minutes, about $10 to $20 at API prices; on a subscription it counts against your usage limits.

## Reviews and credit

The [PR template](../../.github/pull_request_template.md) asks for the checks and the credit.
Credit an agent in the PR description as the [conventions](../conventions.md#names-branches-prs-commits) say, never with a `Co-authored-by:` trailer.
