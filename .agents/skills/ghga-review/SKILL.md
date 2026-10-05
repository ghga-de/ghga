---
name: ghga-review
description: Review a branch or pull request against the GHGA standards, the area AGENTS.md files, the writing style and the naming grammar, and against the issue it names. Run as /ghga-review, next to the built-in /code-review, which looks for bugs.
disable-model-invocation: true
---

# Standards review

The built-in `/code-review` looks for bugs; this skill checks a change against the rules the repo writes down.
Run both before asking a person for review.

## Gather

1. Find the change: for a PR, `gh pr view <n> --json title,headRefName,baseRefName,body` and `gh pr diff <n>`.
   For a branch, diff against its base: `git diff <base>...HEAD` and `git log <base>..HEAD`, where the base is `origin/dev`, `origin/main` for a hotfix, or the branch below it in a stack.
2. Read the root `AGENTS.md` and the `AGENTS.md` of every area the diff touches, `docs/style.md`, and the names section of `docs/conventions.md`.
3. If the branch or title names a YouTrack key or an epic the session can read, compare the change with what it asks for.

## Check

- **Comments and docstrings** explain why, not history: dates, incidents, people and "used to" belong in the commit message ([style](../../../docs/style.md)).
- **Tests:** a behaviour change comes with a test in the member's own suite; a flow across services belongs in the test bed ([test levels](../../../AGENTS.md#test-levels)).
- **Docs:** a changed API, event schema, config or cross-service flow updates its docs, or the description says why not.
- **Names:** the branch against the grammar, which no tool checks; the description against its length and the credit rule ([conventions](../../../docs/conventions.md#names-branches-prs-commits)).
- **Area rules:** whatever the touched area's `AGENTS.md` asks for, such as the service patterns in `services/AGENTS.md`.

Skip what a tool already catches: ruff, mypy, eslint, rumdl, the pre-commit hooks that CI runs on every file (generated service docs, the ADR and epic indexes, `docs_check.py`), `uv sync --locked`, and the `pr-title` workflow.

## Report

1. Check each finding before reporting it: read the code around it, and for a claim about behaviour run the command that shows it, such as `just test <member>`.
2. Rate each from 0 to 100 for how sure you are that it breaks a written rule, and report only those at 80 or above.
3. One finding per line, `path:line — problem. Fix.`, with `nit:` in front of a small one and `q:` in front of a question; the branch and the description take their name in place of the path.
4. When nothing reaches 80, say so in one line.
5. Report in the session and change no file: the author fixes.
   Post to the PR only when asked, with `gh pr review <n> --comment`: at most about ten findings inline, never a `nit:`, the rest in the review's summary.
