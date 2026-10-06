# Instruction files for coding agents

Where guidance for coding agents lives and what belongs in each file.
The decision behind it is [ADR-0042](adrs/adr-0042-agent-instruction-files.md); how to write the text is in the [writing style](style.md), and what the format itself guarantees is at [agents.md](https://agents.md).

## The four kinds of file

| File | Holds | Written for | Loaded |
|---|---|---|---|
| `AGENTS.md` | how we work here: placement, commands, execution policy, definition of done | agents first, but it binds people too | always, the root file plus the area in hand |
| `README.md` | what the thing is, how to install and run it; published, so it stands alone | humans first, agents read it too | on demand |
| `docs/` — [style](style.md), [conventions](conventions.md), ADRs, architecture | the rules themselves | both, written once | on demand, when a task touches them |
| `.agents/skills/` | the steps of a recurring task | agents only | when the skill is invoked |

How a file is written depends on who reads it.
Who has to follow it is a separate question, answered in [Keeping them true](#keeping-them-true).

`AGENTS.md` instructs.
Its reader has the repository open and a task in hand, so it can name the command to run and the mistake to avoid, and leave out everything else.
A README explains: its reader may have no checkout and no task, and needs to know what the thing is before anything else.
`docs/` states a rule once, in a form that serves both readers.
A skill is a step-by-step procedure, written to be followed rather than read.

A rule lives in one place.
`docs/style.md` says *how* to write an ADR, a commit message or a comment; `AGENTS.md` says only *that* writing follows it, and when to go and read it.
The same holds for the conventions and the README: `AGENTS.md` carries the pointer and the trigger, never a summary that can drift from its source.

## Areas

An `AGENTS.md` covers an area, not a member — the 32 workspace members share the rules of the directory they sit in:

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

`AGENTS.md` is the only file with instructions in it.
Claude Code reads it natively, from v2.1.277 on, and no `CLAUDE.md` is committed: one in or above the working directory makes Claude Code read it instead of every `AGENTS.md`.
Personal instructions stay out of the repo; [dev/using-agents.md](dev/using-agents.md#personal-setup) says where they go.

Copilot gets one stub, `.github/copilot-instructions.md` at the repo root, which points at `AGENTS.md` and holds nothing else.
Copilot reads the root `AGENTS.md` by itself but finds the nested ones only with `chat.useNestedAgentsMdFiles`, which is set in the committed `.vscode/settings.json`.

## AGENTS.md and README.md

A README addresses the reader arriving at the code; `AGENTS.md` addresses the one already changing it.
The README says what the thing is and how to install and run it, and it is published — on PyPI and the docs site — so it has to stand without the repo around it.
`AGENTS.md` says which of those commands to prefer, when, and what not to do.

Where a passage serves both readers it goes in the README, and `AGENTS.md` links it.
[`frontend/data-portal/AGENTS.md`](../frontend/data-portal/AGENTS.md) is the model: its `Test levels` section states the rule and links `Automated tests` for the reasoning.

The references are asymmetric.
`AGENTS.md` links the README freely — that is what keeps it short.
A README links back once at most: a line telling a human contributor that the file governs agents and is to be kept current.

## Placement

- A passage belongs in the root file only if it holds for every area.
  Anything narrower moves down, with a pointer left where an agent would still look for it; anything needed only while doing one named task moves into a skill.
- Aim at 100 to 150 lines per file.
  Past that, agents read it less reliably and every line dilutes the ones around it.
- Everything an agent needs is reachable from an `AGENTS.md`.
  A document nothing links is read in under a tenth of sessions, so a new one either earns a pointer or is not worth writing.

## Skills

Reusable task procedures live in `.agents/skills/<name>/SKILL.md`.
Only a name and a description load until the skill is invoked.
The folder-with-a-`SKILL.md` shape is the [Agent Skills](https://agentskills.io) standard — open and stewarded like `AGENTS.md`; `.agents/skills/` is its tool-agnostic location, and our own dependencies ship skills there.

Shared skills sit in the root `.agents/skills/`, flat, one directory per skill, named after its task.
A skill for one area says so in its `paths` frontmatter field, a list of globs such as `services/**`: Claude Code and Cursor list it once the agent reads a matching file, and the other tools list it everywhere.
Only a skill about one member's internals stays nested in that member, as the `libs/ghga-jsonsubschema` ones do, because Copilot CLI, OpenCode and Codex find a nested skill only in a session started there.
The [skill catalogue](agent-skills.md) is generated from the frontmatter and lists every skill, where it applies and who invokes it.

The frontmatter holds the fields of the [specification](https://agentskills.io/specification): `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`.
Of Claude Code's own fields, only `disable-model-invocation`, `user-invocable` and `paths` are allowed, since they only narrow when a skill loads and the other tools ignore them without harm.

A third-party skill, such as Google's `angular-developer`, is a pinned copy in the root `.agents/skills/`, with its source and full commit SHA in `metadata` and a `paths` field of ours.
Nothing else in it is edited, so a newer copy replaces it whole; the Angular one moves to the branch of [angular/skills](https://github.com/angular/skills) that matches the portal's Angular version when the portal upgrades.
The Markdown lint and `just prose` skip it.
Where it disagrees with our docs, a skill of ours names the difference and takes priority, as `data-portal` does.

Claude Code reads `.claude/skills/` only, so each skill gets a symlink, `.claude/skills/<name>` → `../../.agents/skills/<name>`, beside the same `.agents/`: in the root for a root skill, in the member for a nested one.
Its documentation supports this, and the symlink goes when Claude Code reads the standard path.

The links are relative and committed: git stores a symlink as its target path, so a clone gets working links without a setup step.
Generating them instead, from a recipe or a container hook, would leave the skills missing for everyone who has not run it.

A Windows checkout without `core.symlinks` gets text files instead, and the skills go quiet there.
[ADR-0042](adrs/adr-0042-agent-instruction-files.md) accepts that: the devcontainer is the intended environment, and a skill that fails to load costs one procedure, not every rule at once.

`AGENTS.md` names the directory and says no more about it: the tools list the skills they find, and an index in prose would only duplicate them and go stale.
The line is there so an agent without skill support knows the directory holds procedures it can read as plain Markdown.
The catalogue does not count as such an index: it is generated, and only a person opening it loads it.

A passage is a skill when it is only needed while doing one named task and runs to more than a couple of lines — writing an ADR, cutting a release, running the test bed, regenerating the charts.
It stays in `AGENTS.md` when it changes how any task is done.

### Admitting a skill

Every description the model is offered costs context in each session that sees it, so a skill joins the shared set, committed and model-invoked, only if all of these hold:

- **Frequent:** most devs of its area do the task at least monthly; a root skill counts everyone.
- **Repo-specific:** it carries our conventions, commands and traps, and no sentence the model would follow unprompted.
- **Beats the baseline:** on an eval of at least 5 cases with 3 runs per arm, graded by checks fixed before the run, it scores higher than a session without it; a tie is a rejection.
- **Points, does not restate:** it links the rule in `docs/` or an `AGENTS.md` and holds only the order of steps, the commands and the traps.
- **Small:** a description under 300 characters with the key use case first, and a body under about 100 lines; longer material goes into `references/` files the body links.

A useful skill that fails the first or the third test is user-invoked instead (`disable-model-invocation: true`): committed, started only by a person, and its description stays out of the model's context.
Anything else stays personal ([dev/using-agents.md](dev/using-agents.md#personal-setup)).

The budget for what the repo puts into a session before any task, at characters divided by 4:

| Session | Counts | Ceiling |
|---|---|---|
| root | the root `AGENTS.md`, the output style, the descriptions of model-invoked root skills without `paths` | 4k tokens |
| an area | the above, every `AGENTS.md` down to the area, every model-invoked description offered there | 7k tokens |
| any | the skill descriptions alone | 1.5k tokens |

The last ceiling leaves room for personal skills: Claude Code gives the skill listing 1% of the context window and drops descriptions past it.
`just docs-check --budget` prints each session's figures.

A root skill's eval suite is one file, `.agents/skills/<name>/evals.yaml`, and `just skill-eval <name>` expands it into the case directories `claude plugin eval` reads and runs it.
Each case runs 3 times with the skill and 3 times without it, in a clone at a pinned commit that `scripts/skill-eval-scaffold.sh` prepares without the root skills.
Neither arm loads the project's settings, hooks or `AGENTS.md`, so each case tells the agent to read the root `AGENTS.md` first.
A pass is due when the skill's `SKILL.md` changes, and for every suite when `SKILL_EVAL_MODEL` in the justfile moves to a new default model.
Passes run by hand; a CI workflow follows once a few passes show stable scores.
A grader changed after a run means rerunning the whole suite, and moving the pin means checking each case's expected values against the new commit.

The PR that adds or changes a shared skill shows the reviewer:

- the evidence for each test above, with the eval result of both arms;
- that the `name` clashes with no built-in command and no popular public skill, such as `code-review` or `commit`;
- each frontmatter field beyond `name` and `description`, with its reason;
- for a third-party skill, its source URL, commit SHA and licence in `license` and `metadata`;
- the budget figures after the change, and what `/doctor prompt-audit` reports about the skill.

Skills are reviewed each quarter: one unused for two quarters, or no longer beating the baseline after a model change, is removed.

## Keeping them true

The rules in an `AGENTS.md` are the team's rules — branch names, test scoping, the definition of done — so people follow them too.
Only the few that describe how an agent is to behave, such as not committing unless asked, apply to agents alone.

An agent may improve the file it works under, and often should: it is the one that finds an instruction ambiguous, contradicted by the code, or followed to a wrong result.
It proposes the change as a diff in a pull request, reviewed like any other, never as a silent edit in the middle of another task.

Two limits, because the instinct is always to add a line:

- **An addition says what it replaces.**
  The file has a size budget, and a rule earned in one session dilutes the ones that hold in all of them.
- **No war stories.**
  "This once broke X" belongs in the commit message; the file states the rule and, where it is not obvious, why it holds — the same test the [writing style](style.md) applies to comments.

## Checks

`scripts/docs_check.py` ([ADR-0041](adrs/adr-0041-docs-linting.md)) fails when a `CLAUDE.md` is committed, the Copilot stub carries content of its own, or an instruction file sits at a path no tool reads.
It fails, too, when a skill's `name` differs from its directory or leaves the specification's pattern, its description is missing or longer than 1024 characters, its frontmatter has a field not listed above, a relative link in it resolves to nothing, or its `.claude/skills/` symlink is missing or points elsewhere.
It warns, without failing, about a description past 300 characters and a session past its budget, and it regenerates the [skill catalogue](agent-skills.md).

## Not adopted

Options considered and left out, with the signal to look again.

- **Copilot code review.**
  An automatic review of every PR needs Copilot Business or Enterprise, or premium requests paid by the org, and the team has neither.
  Look again if the org gets Copilot.
- **Usage telemetry.**
  Claude Code can export OpenTelemetry events that name the skill behind each request, which would show the team's skill use for the quarterly review.
  It needs a collector and an opt-in in each dev's `~/.claude/settings.json`, since committed settings would also export outside contributors' sessions.
  Look again if the `/skill-doctor` reports leave the review guessing.
