# Agent skills

A skill is a task procedure for coding agents in `.agents/skills/<name>/SKILL.md`.
Until the skill is invoked, only its name and description load.
Where skills live and what earns one a place is in [agent-instructions.md](agent-instructions.md#skills).

The table is generated from each skill's frontmatter by `just docs-check`; do not edit it by hand.
"Invoked by" says whether the model may load the skill on its own, a person can start it with its slash command, or both.

<!-- skill-index:start -->
| Skill | Applies | Invoked by | Description |
|---|---|---|---|
| [adr](../.agents/skills/adr/SKILL.md) | whole repo | model or `/adr` | Write, amend or supersede an architecture decision record in docs/adrs/. Use when asked to record a decision, or to draft, change or replace an ADR. |
| [angular-developer](../.agents/skills/angular-developer/SKILL.md) | `frontend/**` | model or `/angular-developer` | Generates Angular code and provides architectural guidance. Trigger when creating projects, components, services, or HTTP communication, or for best practices on reactivity (signals, linkedSignal, resource, httpResource), forms, dependency injection, routing, SSR, accessibility (ARIA), animations, styling (component styles, Tailwind CSS), testing, naming conventions, or CLI tooling. |
| [data-portal](../.agents/skills/data-portal/SKILL.md) | `frontend/data-portal/**` | model or `/data-portal` | Use first for any change in frontend/data-portal/. Holds the portal's own Angular conventions and test rules, and wins where angular-developer disagrees. |
| [doc-lookup](../.agents/skills/doc-lookup/SKILL.md) | whole repo | `/doc-lookup` | Find the passage in the repo docs that answers a question about a design decision, a convention, a release or migration step, or how a service or flow behaves. Use before changing behaviour you do not know, or when asked "which ADR", "why" or "how does X flow". |
| [epic](../.agents/skills/epic/SKILL.md) | whole repo | `/epic` | Write a new epic specification in docs/epics/. Use when asked to draft, plan or name an epic. |
| [ghga-review](../.agents/skills/ghga-review/SKILL.md) | whole repo | `/ghga-review` | Review a branch or pull request against the GHGA standards, the area AGENTS.md files, the writing style and the naming grammar, and against the issue it names. Run as /ghga-review, next to the built-in /code-review, which looks for bugs. |
| [pr-and-commit](../.agents/skills/pr-and-commit/SKILL.md) | whole repo | `/pr-and-commit` | Name a branch, title and describe a pull request, draft the squash commit at merge time, or reply to a review comment, by the GHGA naming grammar. Use when asked to write a PR description, draft the merge commit, name the branch or answer a reviewer. |
| [release](../.agents/skills/release/SKILL.md) | whole repo | `/release` | Cut a GHGA release by tag, a platform release or candidate or a PyPI release of one member or the whole lane, with the checks before each step that cannot be undone. Run as /release with a name and a version, such as /release ghga 15.4.0 or /release hexkit. |
| [testbed](../.agents/skills/testbed/SKILL.md) | `testbed/**` | model or `/testbed` | Write or change a test-bed feature, or find why a test-bed run failed, timed out or still shows the old behaviour. Use for features and steps under testbed/ and for any failure of just testbed. |
| [debug-subschema](../libs/ghga-jsonsubschema/.agents/skills/debug-subschema/SKILL.md) | `libs/ghga-jsonsubschema/` | model or `/debug-subschema` | Investigate why is_subschema returns an unexpected result or raises, by inspecting the canonicalization/simplification pipeline and per-type checkers. Use when debugging a wrong/surprising subtype verdict, an "unsupported" exception, or when adding support for a new schema feature. |
| [jsonsubschema-references](../libs/ghga-jsonsubschema/.agents/skills/jsonsubschema-references/SKILL.md) | `libs/ghga-jsonsubschema/` | model or `/jsonsubschema-references` | The JSON Schema draft-4 spec, how draft 4 differs from later drafts, and the API pitfalls of the pinned greenery, portion, jsonref and jsonschema versions. Use when unsure about a keyword's semantics or before changing code that calls into these libraries; do not answer from memory. |
| [sync-upstream](../libs/ghga-jsonsubschema/.agents/skills/sync-upstream/SKILL.md) | `libs/ghga-jsonsubschema/` | `/sync-upstream` | Compare this fork against IBM/jsonsubschema upstream and port over relevant fixes or check for divergence. Use when asked to sync with upstream, port an upstream commit/PR, or check whether an upstream bug exists here. |
<!-- skill-index:end -->
