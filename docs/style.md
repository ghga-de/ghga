# Writing style for coding agents

The rules coding agents follow when they write docs, comments, commits and pull requests
in this repo. It does not cover user-facing text, such as data portal content, user
documentation or notification emails, which may follow a different style.
It covers only what is settled so far. Commit messages, branch names and pull request
titles follow the [conventions](conventions.md#names-branches-prs-commits), decided in
[ADR-0038](adrs/adr-0038-branching-strategy.md).

## Writing

- **Short and precise above all.** One exact sentence beats three approximate ones; cut
  every sentence the reader would not miss. As a default, keep paragraphs to 3
  sentences, sentences to 25 words and pull request descriptions to 3 paragraphs.
- **Write for the reader in front of the text**: a reviewer with the diff open, a
  developer reading the code now, someone scanning `git log`. Assume fluent non-native
  English and the vocabulary of computer science and biology, not that of other fields.
  Say what they need, in the order they need it, and stop.
- **Plain language.** Short sentences, concrete words, no hype or filler ("robust",
  "seamless", "leverage", "it's worth noting"). One word, one meaning: *register* reads
  as a registry, not as a way of writing, so use the everyday word or say what you mean.
  The word count is not the test: if you have to read your own sentence twice, split it.
- **Link instead of restating.** A rule lives in one place — an ADR, the conventions,
  this file — and everything else points to it.
- **Headings carry no trailing punctuation.** A heading is a label, not a sentence: a
  colon belongs on the paragraph or bold lead-in introducing a list, not on the heading.
- **Comments explain why, not history.** State why the code is the way it is, where the
  code does not show it. Incidents, dates and "this used to be X" belong in the commit
  message.
- **Pull request descriptions** are a few short paragraphs on what changed, why, and
  what to look at; no headings for a small change. Detail that does not fit goes in the
  commit body.

## Length

Agents read these files as well as people, so every extra paragraph costs context
tokens as well as a developer's attention.

| Text | Target |
|---|---|
| Pull request description | Up to 3 short paragraphs, about 150 words |
| Commit message body | 3 to 5 bullets, per the [conventions](conventions.md#names-branches-prs-commits) |
| Code comment | One line, a few at most |
| ADR | About 500 words; the Summary alone about 80. Long analysis goes into an architecture document that the ADR links to |
| Epic specification | As short as possible, as detailed as the work needs; link to ADRs and architecture documents instead of restating them |
| Architecture document | As long as the subject needs; open with a summary of up to 10 lines and use headings, so a reader can load a single section |

## Line wrapping

Files in the repo are read in diffs and review, so their prose is **hard-wrapped at 88
columns**. That is the ruff `line-length` and the data portal's prettier `printWidth`,
so one number covers code and docs.

- **Applies to** Markdown docs, ADRs, READMEs, `AGENTS.md` files and skills.
- **Not wrapped:** tables, headings, code blocks, link URLs that do not fit on a line,
  and front-matter values.
- **Soft-wrapped (one line per paragraph):** text written in a GitHub web form — pull
  request descriptions, review and issue comments, release notes. GitHub renders a hard
  newline in a comment as a visible line break.
- **Commit messages:** subject and body wrapped at 72, per the conventions.
- **Exempt:** [`docs/epics/`](epics/) and ADRs 0001 to 0024 in [`docs/adrs/`](adrs/),
  which were imported with their own formatting.

Wrap the text you write or rewrite. Do not reflow untouched paragraphs to fix their
width by hand: it buries the real change in the diff.

## Architecture decision records

### Shape

Start every ADR from [`adrs/adr-template.md`](adrs/adr-template.md). Name the file
`adr-NNNN-kebab-case-title.md`, with the next free number.

- **Frontmatter:** a YAML block with the [fields below](#header-fields-and-status), in
  that order ([ADR-0040](adrs/adr-0040-adr-frontmatter.md)). No `deciders` field — a
  decision is the team's, and git records who wrote the file.
- **Title:** `# ADR-NNNN — <Title>`, in sentence case, right after the frontmatter.
- **`## Summary`:** one Y-statement, one clause per paragraph, with the content of each
  clause in bold. A reader who stops here should know what was decided, instead of what,
  and at what price.
- **`## Details`:** the subsections `### Context`, `### Decision`, `### Consequences`
  and `### Alternatives`, in that order. Further subsections go after
  `### Alternatives`, or as `####` headings inside one of them.

An ADR records a decision and why it was taken. Keep out of it what goes stale first:
implementation checklists belong in the pull request or a runbook, and editorial intent
("to be merged into ADR-0031") belongs in a pull request description.

### Header fields and status

| Field | Value |
|---|---|
| `status` | One word from the list below. Always present. |
| `date` | `YYYY-MM-DD` the ADR was accepted, or proposed while in review. Always present. |
| `amended` | `YYYY-MM-DD` of the latest amendment. Only if amended. |
| `supersedes` | List of the ADRs this one replaces, e.g. `[ADR-0024]`. Only if any. |
| `superseded-by` | List with the ADR that replaces this one. Only with `superseded`. |
| `tags` | List of one or more tags from the list below. Always present. |
| `related` | List of other ADRs a reader of this one should know. Only if any. |

Status values, the set [MADR](https://adr.github.io/madr/) uses:

| Status | Meaning |
|---|---|
| `proposed` | Open for review; not binding yet. Set to `accepted` in the pull request before it merges. |
| `accepted` | Binding. |
| `rejected` | Considered and turned down; kept for the reasoning. |
| `deprecated` | No longer binding, and nothing replaces it. |
| `superseded` | No longer binding; `superseded-by` names the replacement. |

Tags, for finding ADRs by topic: `backend`, `frontend`, `data`, `events`, `security`,
`build`, `release`, `deploy`, `testing`, `docs` and `process`. Extend this list before
using a new tag, and `TAGS` in `scripts/docs_check.py` with it.

The status tracks the decision, not its implementation. An ADR does not discuss whether
it has been carried out, except as a side note where a reader needs it.

When part of an accepted decision changes but the decision as a whole stands, amend it
instead of writing a new ADR. Set `amended` to the date and describe the change at the
passage it affects, starting with `**Amended YYYY-MM-DD:**`. Change that is large
enough to replace the decision gets a new ADR that supersedes the old one.

The index in [`docs/README.md`](README.md#decisions-adrs) is generated from the
frontmatter. `scripts/docs_check.py` checks these rules and every ADR reference in the
tree, and regenerates the index ([ADR-0041](adrs/adr-0041-docs-linting.md)). The same
script checks the epics and their index; it runs as a pre-commit hook and as
`just docs-check`.
