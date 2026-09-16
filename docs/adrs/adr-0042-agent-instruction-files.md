---
status: proposed
date: 2026-09-16
tags: [docs, process]
related: [ADR-0033, ADR-0041]
---

# ADR-0042 — Layered AGENTS.md for coding agents

## Summary

In the context of **coding agents working across a Python workspace, an Angular front
end, a forked library and the delivery tooling**

facing **a separate instruction file per tool, area rules crowding the monorepo file,
and every session loading all of it before a word is typed**

we decided for **[the `AGENTS.md` format](https://agents.md) as the only always-on
instruction text, one per area, each with a thin `CLAUDE.md` stub beside it and one
`.github/copilot-instructions.md` at the root, with the rules themselves in `docs/` and
task procedures in skills**

and neglected **a symlink from `CLAUDE.md`, a file per workspace member, and keeping
tool-specific guidance in tool-specific files**

to achieve **one text to maintain per area, readable by any agent, and a root file
carrying only what holds everywhere and is needed every time**

accepting that **an area pays one stub per tool, Claude Code reaches `AGENTS.md` only
through an import, and Copilot needs a setting to find the nested files**.

## Details

### Context

[AGENTS.md](https://agents.md) is an open format for instructing coding agents —
"a README for agents" — stewarded by the Agentic AI Foundation under the Linux
Foundation and read by Codex, Copilot, Cursor, Zed, Aider and some twenty more. It
prescribes no headings: the file is plain Markdown, and an agent reads the nearest one
in the directory tree, so a subproject ships its own and it takes precedence. That
nesting rule is what makes the layering below a property of the format rather than a
local invention.

The repo already carries three `AGENTS.md` files — the monorepo one (1484 words), the
[data portal's](../../frontend/data-portal/AGENTS.md) (2277) and
[`ghga-jsonsubschema`'s](../../libs/ghga-jsonsubschema/AGENTS.md) (1013) — each with a
`CLAUDE.md` beside it. The pattern works, but it is not written down, so it has drifted:
the monorepo file names a `.github/copilot-instructions.md` that does not exist, the
data portal's `CLAUDE.md` holds MCP guidance found nowhere else, and
`docs/epics/.copilot/instructions.md` sits at a path no tool reads.

Support differs by tool. Codex, Cursor and Copilot read `AGENTS.md`, Copilot since
[August 2025](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/),
though nested files need `chat.useNestedAgentsMdFiles` in VS Code and are still uneven
in its CLI. Claude Code has no native support
([issue #34235](https://github.com/anthropics/claude-code/issues/34235)) and discovers
nested files only as `CLAUDE.md`, so a stub per area is what makes the layering work
there at all.

A README sits beside every one of these, and the pair already drifts: the
`ghga-jsonsubschema` README repeats the `uv sync` and `pytest` lines its `AGENTS.md`
also carries.

Measurements published by
[Augment Code](https://www.augmentcode.com/blog/how-to-write-good-agents-dot-md-files)
put the useful size of such a file at 100 to 150 lines with a handful of referenced
documents beside it, and rank discovery: the `AGENTS.md` itself is read every session, a
document it links in about nine of ten, a directory README in eight, a nested README in
four, and a document nothing references in fewer than one. Our root file is 194 lines
and the data portal's 264; `docs/epics/.copilot/instructions.md` is the orphan case.

Loading is the other force. The root `CLAUDE.md` imports the
[style](../style.md) and [conventions](../conventions.md) with `@`, so about 4200 words
enter every session, whether or not it writes an ADR — and `@` is Claude syntax that
other agents read as noise.

### Decision

The layout is written up in
[`docs/agent-instructions.md`](../agent-instructions.md), which every `AGENTS.md` links;
it is the place to look up what belongs in which file. The decision itself:

- **`AGENTS.md` is the only file with instructions in it.** Every tool that cannot read
  it gets a stub that points at it and holds nothing else: a `CLAUDE.md` beside each
  `AGENTS.md`, whose first line is the `@AGENTS.md` import Anthropic documents for this,
  and one `.github/copilot-instructions.md` at the root. A new tool gets another stub,
  never a second copy of the text.
- **Areas, not members.** A set covers the repo root, `frontend/data-portal/`,
  `libs/ghga-jsonsubschema/`, `libs/`, `services/`, `deploy/` and `testbed/` — the
  places whose working rules genuinely differ. The 35 members share theirs.
- **Four kinds of file, told apart by what they hold and when they load:** `AGENTS.md`
  how we work here, always on; `README.md` what the thing is, published and standing on
  its own; `docs/` the rules themselves, read when a task touches them; and
  `.claude/skills/` the steps of a recurring task, read when invoked. A rule lives in
  one of them, and the others link it.
- **Placement follows the loading cost.** A passage belongs in the root file only if it
  holds for every area; anything narrower moves down, and anything needed only while
  doing one named task becomes a skill. Each file aims at 100 to 150 lines, and nothing
  an agent needs is left unlinked.
- **No eager imports beyond the area file.** The style and conventions are linked, not
  `@`-imported, and read when a session needs them.
- **`scripts/docs_check.py` enforces the shape** ([ADR-0041](adr-0041-docs-linting.md)):
  every `AGENTS.md` has its stubs, a stub carries no content of its own, and no orphan
  instruction file sits at a path no tool reads.

### Consequences

- Guidance is written once per area and read by every agent, so adopting one costs a
  stub instead of a migration.
- A root session starts about 2600 words lighter, and an area session loads its own
  rules only when it touches that area.
- The root file keeps rules and loses how-to prose, which moves to `docs/` or a skill
  and is read only when it matters. Both it and the data portal's have to shrink to
  reach 150 lines, and that split is most of the work.
- The layout is a document of its own, so it is one more file to keep true — but it is
  the file the `AGENTS.md` files link instead of restating it seven times.
- Splitting the root file is a one-off edit of prose that already exists, and the
  placement rule is a judgement call the check cannot make.
- Skills are a Claude Code and Copilot feature, not part of the `AGENTS.md` standard.
  An agent without support still reads them as Markdown once pointed at the directory,
  so the split costs a line, not portability.
- The data portal's MCP section moves into its `AGENTS.md`, and
  `docs/epics/.copilot/instructions.md` is deleted; `docs/epics/README.md` already
  carries what it said.
- Copilot needs `chat.useNestedAgentsMdFiles` in the committed `.vscode/settings.json`,
  and its CLI may still read only the root file until the gap closes.

### Alternatives

- **Symlink `CLAUDE.md` to `AGENTS.md`.** Anthropic documents it, but it hides the
  indirection in a file listing, and Windows checkouts and some editors do not follow
  it.
- **An `AGENTS.md` per workspace member.** 35 files that would mostly repeat each other,
  and drift one by one; the rules that differ are per area.
- **Tool-specific content in tool-specific files.** What we have now — the same rule in
  two places, and the second one goes stale.
- **One root file and nothing nested.** Every session would pay for the Angular and
  chart rules, and the file would pass 5000 words within the year.
- **Task procedures in `docs/` rather than in skills.** Every agent can read them, but
  nothing pulls them in at the moment they apply, so the agent has to be told they
  exist — the always-on cost we are trying to avoid.
- **Keeping the `@` imports for style and conventions.** Convenient when writing docs,
  expensive in every session that does not.
