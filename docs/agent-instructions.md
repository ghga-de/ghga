# Instruction files for coding agents

Where guidance for coding agents lives and what belongs in each file. The decision
behind it is [ADR-0042](adrs/adr-0042-agent-instruction-files.md); how to write the text
is in the [writing style](style.md), and what the format itself guarantees is at
[agents.md](https://agents.md).

## The four kinds of file

| File | Holds | Read |
|---|---|---|
| `AGENTS.md` | how we work here: placement, commands, execution policy, definition of done | always, the root file plus the area in hand |
| `README.md` | what the thing is, how to install and run it; published, so it stands alone | on demand |
| `docs/` — [style](style.md), [conventions](conventions.md), ADRs, architecture | the rules themselves, written once for humans and agents alike | on demand, when a task touches them |
| `.claude/skills/` | the steps of a recurring task | when the skill is invoked |

A rule lives in one place. `docs/style.md` says *how* to write an ADR, a commit message
or a comment; `AGENTS.md` says only *that* writing follows it, and when to go and read
it. The same holds for the conventions and the README: `AGENTS.md` carries the pointer
and the trigger, never a summary that can drift from its source.

## Areas

An `AGENTS.md` covers an area, not a member — the 35 workspace members share the rules
of the directory they sit in:

| Area | What its file carries |
|---|---|
| repo root | the tech stack, `just`, branching, execution policy, definition of done |
| `frontend/data-portal/` | Angular, pnpm, MSW mocking, front-end test levels, its MCP servers |
| `libs/ghga-jsonsubschema/` | the upstream fork, its own conventions and pitfalls |
| `libs/` | the PyPI lane, semver per member, what a change costs its consumers |
| `services/` | hexkit ports and adapters, the rest/consumer pair, settings from env |
| `deploy/` | the chart generator against the generated charts |
| `testbed/` | its own `.venv-testbed`, pytest-bdd and Playwright, resets |

## The stubs

`AGENTS.md` is the only file with instructions in it. Each tool that cannot read it gets
a stub that points at it, and nothing else. For Claude Code, a `CLAUDE.md` beside every
`AGENTS.md`, whose **first line is the import**:

```markdown
@AGENTS.md

# Claude Code instructions

`AGENTS.md` holds the instructions for every agent. This stub exists because Claude Code
does not read that file yet.
```

For Copilot, one `.github/copilot-instructions.md` at the repo root, of the same shape.
Copilot reads the root `AGENTS.md` by itself but finds the nested ones only with
`chat.useNestedAgentsMdFiles`, which is set in the committed `.vscode/settings.json`.

## AGENTS.md and README.md

A README addresses the reader arriving at the code; `AGENTS.md` addresses the one
already changing it. The README says what the thing is and how to install and run it,
and it is published — on PyPI and the docs site — so it has to stand without the repo
around it. `AGENTS.md` says which of those commands to prefer, when, and what not to do.

Where a passage serves both readers it goes in the README, and `AGENTS.md` links it.
[`frontend/data-portal/AGENTS.md`](../frontend/data-portal/AGENTS.md) is the model: its
`Test levels` section states the rule and links `Automated tests` for the reasoning.

The references are asymmetric. `AGENTS.md` links the README freely — that is what keeps
it short. A README links back once at most: a line telling a human contributor that the
file governs agents and is to be kept current.

## Placement

- A passage belongs in the root file only if it holds for every area. Anything narrower
  moves down; anything needed only while doing one named task moves into a skill.
- Each move leaves a line pointing to where it went.
- Aim at 100 to 150 lines per file. Past that, agents read it less reliably and every
  session pays for it.
- Everything an agent needs is reachable from an `AGENTS.md`. A document nothing links
  is read in under a tenth of sessions, so a new one either earns a pointer or is not
  worth writing.
- State every prohibition with the thing to do instead.

## Skills

Reusable task procedures live in `.claude/skills/`, where they cost a name and a
description until they are invoked. `AGENTS.md` names the directory and says no more
about it: Claude Code and Copilot list the skills they find, and an index in prose would
only duplicate them and go stale. The line is there so other agents know the directory
holds procedures they can read as plain Markdown.

A passage is a skill when it is only needed while doing one named task and runs to more
than a couple of lines — writing an ADR, cutting a release, running the test bed,
regenerating the charts. It stays in `AGENTS.md` when it changes how any task is done.

## Checks

`scripts/docs_check.py` ([ADR-0041](adrs/adr-0041-docs-linting.md)) fails when an
`AGENTS.md` is missing its stubs, a stub carries content of its own, or an instruction
file sits at a path no tool reads.
