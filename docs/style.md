# Writing style for coding agents

The rules coding agents follow when they write docs, comments, docstrings, commits and pull requests in this repo.
It does not cover user-facing text, such as data portal content, user documentation or notification emails, which may follow a different style.
It covers only what is settled so far.
Commit messages, branch names and pull request titles follow the [conventions](conventions.md#names-branches-prs-commits), decided in [ADR-0038](adrs/adr-0038-branching-strategy.md).

## Writing

- **Short and precise above all.**
  One exact sentence beats three approximate ones; cut every sentence the reader would not miss.
  As a default, keep paragraphs to 3 sentences, sentences to 25 words and pull request descriptions to 3 paragraphs.
  Short means fewer sentences, not compressed ones: keep articles and verbs, and spell out arrows and home-made abbreviations.
- **Write for the reader in front of the text**: a reviewer with the diff open, a developer reading the code now, someone scanning `git log`.
  Assume fluent non-native English and the vocabulary of computer science and biology, not that of other fields.
  Say what they need, in the order they need it, and stop.
- **English in the repo.**
  Files, comments, commits and pull requests are in English, whatever language the dev uses in chat.
- **Plain language.**
  Short sentences, concrete words, no hype or filler ("robust", "seamless", "leverage", "it's worth noting").
  One word, one meaning: *register* reads as a registry, not as a way of writing, so use the everyday word or say what you mean.
  The word count is not the test: if you have to read your own sentence twice, split it.
- **No idioms or figures of speech** ("circle back", "get the ball rolling", "on the same page").
  Name the literal action instead, and the literal thing: base, not substrate; required, not load-bearing.
- **"X, not Y" only when the reader would assume Y.**
  Otherwise state X alone.
- **Every prohibition names the alternative.**
  "Don't X" leaves the reader guessing; say what to do instead.
- **Active voice, and imperative mood for anything to be done.**
  "The service validates the token", not "the token is validated"; "add the index before the migration runs", not "the index should be added".
  Name who acts, or tell the reader what to do.
  Put the condition before the command: "if the build fails, read the log".
- **"must" for a requirement, "may" for an option.**
  Drop an optional "should".
- **Link instead of restating.**
  A rule lives in one place — an ADR, the conventions, this file — and everything else points to it.
- **Describe the thing as it is; comments explain why.**
  Docs, docstrings and comments state the current behaviour.
  A comment states why the code is the way it is, where the code does not show it.
  What changed — incidents, dates, "this used to be X" — belongs in the commit message.
- **Pull request descriptions** are a few short paragraphs on what changed, why, and what to look at; no headings for a small change.
  Detail that does not fit goes in the commit body.

## Markdown

Docs are rendered on GitHub and read in an editor, so they are GitHub Flavored Markdown.

- **One `#` heading, the title.**
  Sections are `##` and subsections `###`.
  The level shows where the section sits, not how large its heading should look.
- **Headings in sentence case, naming what the section holds**: "Line wrapping", not "Line Wrapping" or "Notes".
- **Headings carry no trailing punctuation.**
  A heading is a label, not a sentence: a colon belongs on the paragraph or bold lead-in introducing a list, not on the heading.
- **Bullets for what the reader acts on** — steps, requirements, options — and prose for the reasoning around them.
  A paragraph holding three parallel items is a list.

## Length

Agents read these files as well as people, so every extra paragraph costs context tokens as well as a developer's attention.

| Text | Target |
|---|---|
| Pull request description | Up to 3 short paragraphs, about 150 words |
| Commit message body | 3 to 5 bullets, per the [conventions](conventions.md#names-branches-prs-commits) |
| Code comment | One line, a few at most |
| ADR | About 500 words; the Summary alone about 80. Long analysis goes into an architecture document that the ADR links to |
| Epic specification | As short as possible, as detailed as the work needs; link to ADRs and architecture documents instead of restating them |
| Architecture document | As long as the subject needs; open with a summary of up to 10 lines and use headings, so a reader can load a single section |

## Line wrapping

Markdown in the repo is written **one sentence per line**, so a diff shows the sentence that changed ([ADR-0044](adrs/adr-0044-sentence-per-line-markdown.md)).
Lines have no width limit; the editor soft-wraps them.

- **Applies to** every Markdown file: docs, ADRs, epics, READMEs, `AGENTS.md` files and skills.
  A list item or block quote starts each further sentence on its own line, indented to the item's text.
- **Keeps its own shape:** tables, headings, code blocks and front matter.
  So does a row of badges, one per line, between `<!-- rumdl-disable MD013 -->` and `<!-- rumdl-enable MD013 -->`; rumdl would otherwise join it into one line.
- **Soft-wrapped (one line per paragraph):** text written in a GitHub web form — pull request descriptions, review and issue comments, release notes.
  GitHub renders a hard newline in a comment as a visible line break.
- **Code comments and docstrings:** wrapped at 88, the ruff `line-length`.
- **Commit messages:** subject and body wrapped at 72, per the conventions.

rumdl checks the rule in the pre-commit hook and `just lint`, and `just fmt` fixes it.

## Docstrings

Explain a function's purpose shortly; add detail only where the code doesn't already make it obvious.
Follow the simplified Google style already in this repo.

- **Document**: public functions and classes; non-obvious behaviour or side effects; business logic that needs context.
- **Skip**: anything already clear from naming and type hints; parameter names/types, return types, obvious behaviour.
  Document those only when the signature isn't clear.
- **Cover**: the *what* in natural language; constraints, side effects, and edge cases; the *why*/*how* when non-obvious.

## Architecture decision records

### Shape

Start every ADR from [`adrs/adr-template.md`](adrs/adr-template.md).
Name the file `adr-NNNN-kebab-case-title.md`, with the next free number.

- **Frontmatter:** a YAML block with the [fields below](#header-fields-and-status), in that order ([ADR-0040](adrs/adr-0040-adr-frontmatter.md)).
  No `deciders` field — a decision is the team's, and git records who wrote the file.
- **Title:** `# ADR-NNNN — <Title>`, in sentence case, right after the frontmatter.
- **`## Summary`:** one Y-statement, one clause per paragraph, with the content of each clause in bold.
  A reader who stops here should know what was decided, instead of what, and at what price.
- **`## Details`:** the subsections `### Context`, `### Decision`, `### Consequences` and `### Alternatives`, in that order.
  Further subsections go after `### Alternatives`, or as `####` headings inside one of them.

An ADR records a decision and why it was taken.
Keep out of it what goes stale first: implementation checklists belong in the pull request or a runbook, and editorial intent ("to be merged into ADR-0031") belongs in a pull request description.

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
| `proposed` | Open for review; not binding yet. A new ADR starts here even when the team has already agreed. Set to `accepted` in the pull request before it merges. |
| `accepted` | Binding. |
| `rejected` | Considered and turned down; kept for the reasoning. |
| `deprecated` | No longer binding, and nothing replaces it. |
| `superseded` | No longer binding; `superseded-by` names the replacement. |

Tags, for finding ADRs by topic: `backend`, `frontend`, `data`, `events`, `security`, `build`, `release`, `deploy`, `testing`, `docs` and `process`.
Extend this list before using a new tag, and `TAGS` in `scripts/docs_check.py` with it.

The status tracks the decision, not its implementation.
An ADR does not discuss whether it has been carried out, except as a side note where a reader needs it.

When part of an accepted decision changes but the decision as a whole stands, amend it instead of writing a new ADR.
Set `amended` to the date and describe the change at the passage it affects, starting with `**Amended YYYY-MM-DD:**`.
Change that is large enough to replace the decision gets a new ADR that supersedes the old one.

The index in [`docs/README.md`](README.md#decisions-adrs) is generated from the frontmatter.
`scripts/docs_check.py` checks these rules and every ADR reference in the tree, and regenerates the index ([ADR-0041](adrs/adr-0041-docs-linting.md)).
The same script checks the epics and their index; it runs as a pre-commit hook and as `just docs-check`.
