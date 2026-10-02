---
status: accepted
date: 2026-09-16
amended: 2026-10-02
tags: [docs, process]
related: [ADR-0033, ADR-0041]
---

# ADR-0042 — Layered AGENTS.md for coding agents

## Summary

In the context of **coding agents working across the monorepo's Python workspace, front end and delivery tooling**

facing **one instruction file per tool, area rules crowding the root file, and all of it loading into every session**

we decided for **[`AGENTS.md`](https://agents.md) as the only always-on text, one per area, with a pointer stub for each tool that cannot read it, the rules in `docs/` and task procedures in skills**

and neglected **a `CLAUDE.md` symlink, a file per workspace member, and tool-specific guidance in tool-specific files**

to achieve **one text per area, readable by any agent, and a root file carrying only what holds everywhere**

accepting that **each area pays a stub per tool, and Claude Code and Copilot each need a workaround to find them**.

## Details

### Context

[AGENTS.md](https://agents.md) is an open format for instructing coding agents, a README for agents, stewarded by the Agentic AI Foundation under the Linux Foundation and read by Codex, Copilot, Cursor, Zed, Aider and some twenty more.
It doesn't prescribe any particular headings, and an agent reads the nearest file in the directory tree, so a subproject ships its own and it takes precedence.
That nesting rule makes the layering below a property of the format rather than a local invention.
Task procedures have a standard of their own, [Agent Skills](https://agentskills.io) — a folder with a `SKILL.md` under `.agents/skills/`.

The repo carries three `AGENTS.md` files, each with a `CLAUDE.md` beside it.
They came in with the repositories they belong to, which supported coding agents to different degrees ([ADR-0025](adr-0025-consolidate-into-monorepo.md)), so they differ in shape and depth and some point at files that were never written.
That was to be expected; what it needs now is one layout to converge on.

Support differs by tool.
Codex, Cursor and Copilot read `AGENTS.md`, Copilot since [August 2025](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/), though nested files need `chat.useNestedAgentsMdFiles` in VS Code and are still uneven in its CLI.
Claude Code has no native support ([issue #34235](https://github.com/anthropics/claude-code/issues/34235)) and discovers nested files only as `CLAUDE.md`, so a stub per area is what makes the layering work there at all.

**Amended 2026-09-30:** Claude Code reads `AGENTS.md` natively since v2.1.277: the root file at session start, and an area's file once it reads a file there.
It does so only while no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` sits in the working directory or above it.
`chat.useNestedAgentsMdFiles` governs only VS Code's Local agent, which VS Code is retiring; its Agent Host harnesses follow their own rules.

Size and reachability decide whether a file is used.
[Measurements published by Augment Code](https://www.augmentcode.com/blog/how-to-write-good-agents-dot-md-files) put the useful size at 100 to 150 lines with a few referenced documents beside it, and find that a document no `AGENTS.md` references is read in fewer than one session in ten.
Our root file is 194 lines and the data portal's 264.

Loading is the other force.
The root `CLAUDE.md` imports the [style](../style.md) and [conventions](../conventions.md) with `@`, so about 4200 words enter every session whether or not it writes an ADR — but `@` is Claude syntax that other agents read as noise.

### Decision

The layout is written up in [`docs/agent-instructions.md`](../agent-instructions.md), which every `AGENTS.md` links; it is the place to look up what belongs in which file.
The decision itself:

- **`AGENTS.md` is the only file with instructions in it.**
  Every tool that cannot read it gets a stub that points at it and holds nothing else: a `CLAUDE.md` beside each `AGENTS.md`, whose first line is the `@AGENTS.md` import Anthropic documents for this, and one `.github/copilot-instructions.md` at the root.

  **Amended 2026-09-30:** Claude Code reads `AGENTS.md` natively, so the `CLAUDE.md` stubs are removed.
  `docs_check.py` now rejects a committed `CLAUDE.md`, since one file above the working directory switches native reading off.
  Personal instructions go in `~/.claude/CLAUDE.md` or a gitignored `.claude/rules/*.local.md`.
  A dev who keeps a `CLAUDE.local.md`, which is gitignored too, sets Project instructions to `claude-md-and-agents-md` in `/config`, or Claude Code skips `AGENTS.md`.
- **Areas, not members.**
  A set covers the repo root, `frontend/data-portal/`, `libs/ghga-jsonsubschema/`, `libs/`, `services/`, `deploy/` and `testbed/` — the places whose working rules genuinely differ.
  The 35 members share theirs.
- **Four kinds of file, told apart by whom they address, what they hold and when they load:** `AGENTS.md` how we work here, always on; `README.md` what the thing is, published and standing on its own; `docs/` the rules themselves, read when a task touches them; and `.agents/skills/` the steps of a recurring task, read when invoked.
  A rule lives in one of them, and the others link it.
  `AGENTS.md` is written for agents first and a README for humans first, which sets how each is written — not who is bound by it.
  The rules in an `AGENTS.md` are the team's, and an agent changes them by proposing a diff like any other.

  **Amended 2026-10-02:** Shared skills live in the root `.agents/skills/`, flat, one directory per skill, with their symlinks in the root `.claude/skills/`.
  A skill for one area says so in its `paths` frontmatter field: Claude Code and Cursor then list it once the agent works there, and the other tools list it everywhere.
  Only a skill about one member's internals stays nested in that member.
  Copilot CLI, OpenCode and Codex find a nested skill only in a session started in its area.
- **Placement follows the loading cost.**
  A passage belongs in the root file only if it holds for every area; anything narrower moves down, and anything needed only while doing one named task becomes a skill.
  Each file aims at 100 to 150 lines, and nothing an agent needs is left unlinked.

  **Amended 2026-10-02:** A skill joins the shared set, committed and offered to the model, only if most devs of its area use it monthly, it carries repo knowledge the model lacks, and an eval shows it beats a session without it.
  Any other skill is user-invoked (`disable-model-invocation`) or personal.
  The repo's always-on context stays under 4k tokens in a root session and 7k in an area session, at most 1.5k of them skill descriptions; `docs_check.py` warns past each.
- **No eager imports beyond the area file.**
  The style and conventions are linked, not `@`-imported, and read when a session needs them.
- **`scripts/docs_check.py` enforces the shape** ([ADR-0041](adr-0041-docs-linting.md)): every `AGENTS.md` has its stubs, a stub carries no content of its own, and no orphan instruction file sits at a path no tool reads.

  **Amended 2026-10-02:** The check also covers each `SKILL.md`: a `name` equal to its directory and in the spec's pattern, a description of at most 1024 characters (a warning past 300), known frontmatter fields, resolving links and the `.claude/skills/` symlink.
  It reports the context budget and generates the skill catalogue in [`docs/agent-skills.md`](../agent-skills.md), which a person opens and no session loads.

### Consequences

- Guidance is written once per area and read by every agent, so adopting one costs a stub instead of a migration.
- A root session starts about 2600 words lighter, and an area session loads its own rules only when it touches that area.
- The existing files are brought into line in a follow-up: the root and the data portal's shrink toward 150 lines, the areas without one gain it, and what the stubs carry of their own moves into the `AGENTS.md` beside them.
- The layout is one more document to keep true, but it is the one the `AGENTS.md` files link instead of restating it seven times.
  Where a passage belongs stays a judgement call the check cannot make.
- Skills sit at the standard path, so every tool that reads `.agents/skills/` finds them.
  Claude Code reads `.claude/skills/` only, so each skill is symlinked there — documented and supported, and the symlink goes when it reads the standard path.
- Copilot needs `chat.useNestedAgentsMdFiles` in the committed `.vscode/settings.json`, and its CLI may still read only the root file until the gap closes.

### Alternatives

- **Symlink `CLAUDE.md` to `AGENTS.md`.**
  Anthropic documents it, but it hides the indirection in a file listing, and Windows checkouts and some editors do not follow it.
  The skills are symlinked all the same: one that fails to load costs a procedure, not the whole instruction set.
- **An `AGENTS.md` per workspace member.**
  35 files that would mostly repeat each other and drift one by one; the rules that differ are per area.
- **Tool-specific content in tool-specific files.**
  The same rule in two places, and the second one goes stale.
- **One root file and nothing nested.**
  Every session would pay for the Angular and chart rules, and the file would pass 5000 words within the year.
- **Task procedures in `docs/` rather than in skills.**
  Every agent can read them, but nothing pulls them in at the moment they apply.
- **Keeping the `@` imports for style and conventions.**
  Convenient when writing docs, expensive in every session that does not.
