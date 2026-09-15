# Writing style for coding agents

The rules coding agents follow when they write docs, comments, commits and pull requests
in this repo. It does not cover user-facing text, such as data portal content, user
documentation or notification emails, which may follow a different style.
It covers only what is settled so far. Commit messages, branch names and pull request
titles follow the [conventions](conventions.md#names-branches-prs-commits), decided in
[ADR-0038](adrs/0038-branching-strategy.md).

## Writing

- **Short and precise above all.** Walls of text do not get read. One exact sentence
  beats three approximate ones; cut every sentence the reader would not miss. As a
  default, keep paragraphs to 3 sentences, sentences to 25 words and pull request
  descriptions to 3 paragraphs.
- **Write for the reader in front of the text**: a reviewer with the diff open, a
  developer reading the code now, someone scanning `git log`. Say what they need, in the
  order they need it, and stop.
- **Plain language.** Short sentences, concrete words, no hype or filler ("robust",
  "seamless", "leverage", "it's worth noting").
- **Link instead of restating.** A rule lives in one place — an ADR, the conventions,
  this file — and everything else points to it.
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

Start every ADR from [`adrs/0000-template.md`](adrs/0000-template.md). Name the file
`NNNN-kebab-case-title.md`, with the next free number.

- **Title:** `# ADR-NNNN — <Title>`, in sentence case.
- **Header list:** the [fields below](#header-fields-and-status), in that order, one per
  line. They map one to one onto the YAML frontmatter ADRs will get, so keep values
  plain: no prose, no formatting beyond links. No `Deciders` line — a decision is the
  team's, and git records who wrote the file. Older ADRs keep theirs until they are next
  rewritten.
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
| `Status` | One lowercase word from the list below. Always present. |
| `Date` | `YYYY-MM-DD` the ADR was accepted, or proposed while in review. Always present. |
| `Amended` | `YYYY-MM-DD` of the latest amendment. Only if amended. |
| `Supersedes` | Links to the ADRs this one replaces, comma-separated. Only if any. |
| `Superseded by` | Link to the ADR that replaces this one. Only with `superseded`. |

Status values, the set [MADR](https://adr.github.io/madr/) uses:

| Status | Meaning |
|---|---|
| `proposed` | Open for review; not binding yet. Set to `accepted` in the pull request before it merges. |
| `accepted` | Binding. |
| `rejected` | Considered and turned down; kept for the reasoning. |
| `deprecated` | No longer binding, and nothing replaces it. |
| `superseded` | No longer binding; `Superseded by` names the replacement. |

The status tracks the decision, not its implementation. An ADR does not discuss whether
it has been carried out, except as a side note where a reader needs it.

When part of an accepted decision changes but the decision as a whole stands, amend it
instead of writing a new ADR. Set `Amended` to the date and describe the change at the
passage it affects, starting with `**Amended YYYY-MM-DD:**`. Change that is large
enough to replace the decision gets a new ADR that supersedes the old one.

Before renaming, renumbering or deleting an ADR, find and fix every reference to it, and
update the index in [`docs/README.md`](README.md#decisions-adrs).
