---
status: accepted
date: 2026-09-29
tags: [docs, process]
related: [ADR-0036, ADR-0041]
---

# ADR-0044 — One sentence per line in Markdown, checked by rumdl

## Summary

In the context of **Markdown in the repo, written by developers and coding agents and read in diffs and review**

facing **a hard wrap at 88 columns that turns a one-word edit into a reflowed paragraph, and that no tool checks**

we decided for **one sentence per line, enforced and fixed by rumdl, a Markdown linter from the lockfile, in a pre-commit hook and `just lint`**

and neglected **the hard wrap with a formatter, one line per paragraph, markdownlint and mdformat**

to achieve **diffs that show the changed sentence, and one Markdown style checked the same way locally and in CI**

accepting that **raw files show long lines unless the editor soft-wraps, and one sweep commit reflows the tree**.

## Details

### Context

The [writing style](../style.md#line-wrapping) asked for prose hard-wrapped at 88 columns.
Changing a word near the start of a paragraph shifts every line after it, so the diff shows the whole paragraph and review has to find the real change.
Nothing checked the width, so files drifted, and rewrapping by hand was discouraged for the same diff noise.

[ADR-0041](adr-0041-docs-linting.md) checks the ADR and epic structure and leaves the rest of a Markdown file to review.

### Decision

Markdown prose is written one sentence per line, with no width limit.
A list item or block quote follows the same rule inside its indentation.
Tables, headings, code blocks and front matter keep their own shape.

rumdl checks every Markdown file in the repo:

- **It comes from `uv.lock`**, as a `dev` dependency, so the hook, `just lint` and CI run one version ([ADR-0036](adr-0036-pre-commit-hooks.md)).
- **Its configuration** is `[tool.rumdl]` in the root `pyproject.toml`, beside ruff's.
  MD013 runs in sentence-per-line mode, and the default rule set applies except MD033, since the READMEs place images and anchors with inline HTML.
- **The hook fixes** what rumdl can fix and fails the commit, as the ruff hook does, so the fix is to stage the result.
  `just fmt` fixes the whole tree.
  Rules whose fixes proved unreliable in the sweep (MD034, MD037, MD046) only report, so a person picks the markup.
- **Excluded** are only the chart READMEs `just charts` generates; the imported ADRs and epics are checked like any other file, so no legacy rule needs upkeep.
  Per-file ignores cover what a rule misreads, such as the `CLAUDE.md` stubs without a heading and the hexkit guide's links to generated reference pages.

One commit reflows the existing files with `rumdl fmt`, plus a one-off join of wrapped list items, which rumdl leaves alone.
It changes line breaks, not text, apart from what the other rules fix, such as bare URLs and trailing colons in headings.

### Consequences

- A diff of a Markdown file shows the changed sentences, and a merge conflict stays within one.
- Nobody wraps by hand, and an agent's output passes after one `just fmt`.
- rumdl does not flag a single sentence wrapped inside a list item, so review still catches those.
- A long sentence shows as a long line, which makes it visible in review.
- Raw files need soft wrap in the editor; the VS Code workspace settings turn it on for Markdown.
- The sweep commit touches most Markdown files once, so blame on them points to it; it is listed in `.git-blame-ignore-revs`.
- Code comments and docstrings keep the 88-column limit ruff enforces, and commit messages keep 72.

### Alternatives

- **The hard wrap at 88 with a formatter.** mdformat or prettier could keep the width, but every edit still reflows the rest of its paragraph in the diff.
- **One line per paragraph.**
  Needs no tool, but a one-word change marks the whole paragraph as changed.
- **markdownlint.**
  The reference rule set, but it brings the npm toolchain into the Python side, and it has no sentence-per-line fix.
- **mdformat.**
  A formatter only, with width-based wrapping and no lint rules.
