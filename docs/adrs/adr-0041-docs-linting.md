---
status: accepted
date: 2026-09-15
amended: 2026-09-16
tags: [docs, process]
related: [ADR-0036, ADR-0040]
---

# ADR-0041 — A pre-commit check for ADRs and epics

## Summary

In the context of **ADRs with YAML frontmatter and a generated index
([ADR-0040](adr-0040-adr-frontmatter.md)), and epics with a name and layout rule**

facing **rules for fields, headings, shape and references that only review enforces, and
references across the tree that break when files move**

we decided for **a script in `scripts/`, run by two repo-local pre-commit hooks: one
checks the ADR and epic sets and regenerates their indexes when either changes, the
other checks references to both in the files of every commit**

and neglected **markdownlint with a frontmatter schema, a schema check alone, a CI-only
check, and ADR tools with their own format**

to achieve **ADRs that follow the template, epics that follow their layout, indexes
and references that cannot go stale, and the same result locally and in CI**

accepting that **the checks are ours to maintain, and a rule change means changing both
the script and the writing style**.

## Details

### Context

The ADR shape is written down in the
[writing style](../style.md#architecture-decision-records) and checked only in review.
Review missed drift: the index fell behind the files more than once, and renumbering
the set needed a follow-up commit for compound references such as `ADR-0006/0016` that
the sweep missed.

ADR-0040 makes the header machine-readable, which turns most of these rules into checks.
Hook tools come from the lockfiles, and CI's `hygiene` job runs every hook over the
whole tree ([ADR-0036](adr-0036-pre-commit-hooks.md)).

**Amended 2026-09-16:** the epics were renamed and reshaped the same way, so they gained
rules worth checking and an index that a hand-run script kept
([`docs/epics/README.md`](../epics/README.md)). One script covers both, and it is
`scripts/docs_check.py`.

### Decision

`scripts/docs_check.py` checks the ADRs and the epics, run through `uv run` by two
`repo: local` hooks, and by hand through `just docs-check`:

- **The set hook** runs when a commit touches `docs/adrs/`, `docs/epics/` or
  `docs/README.md`. It checks both sets, since most rules span files, and references
  across the tree, since removing or renumbering an ADR can break any of them.
- **The reference hook** runs on every commit, and checks references only in the
  committed files. A new reference can appear in any file, and grepping the staged
  files keeps the cost to the `uv run` startup.

Together they fail when:

- **The file name** is not `adr-NNNN-kebab-case.md`, a number is taken twice, or the
  heading is not `# ADR-NNNN — Title` with the number from the file name.
  **Amended 2026-09-16:** the name carries an `adr-` prefix, so a file listing shows
  the type and the name holds the reference form (`adr-0041` ↔ `ADR-0041`). The
  template is `adr-template.md`, since it has no number to hold.
- **The frontmatter** lacks a required field, has an unknown one, or has a status, date
  or tag outside the values in the writing style.
- **The headings** `Summary`, `Details`, `Context`, `Decision`, `Consequences` and
  `Alternatives` are missing or out of order.
- **Supersession** is one-sided: `superseded-by` needs status `superseded` and a
  matching `supersedes` in the other ADR, and the reverse.
- **A reference dangles:** an `ADR-NNNN` mention, including compound forms such as
  `ADR-0028/0035`, or a link into `docs/adrs/` or `docs/epics/`, in any tracked text
  file, names an ADR or epic that does not exist.
- **An epic name, shape or header is wrong:** the name is not `epic-NNNN-kebab-case`, a
  number is taken twice, the first heading is not `# Description (Code Name)`, the
  `**Epic Type:**` line is missing or names something outside the three types, or a
  directory holds no `README.md` — or nothing besides it, where a single file is the
  shape.

The set hook also regenerates the ADR index in `docs/README.md` and the epic index in
`docs/epics/README.md`, and fails when that changed a file, as the whitespace fixers do,
so the fix is to stage the result. It replaces the hand-run `docs/epics/create_toc.py`.

The script has unit tests in `scripts/tests/`. Prose rules, such as length and the
wording of the Summary, stay with review.

### Consequences

- A broken ADR or reference fails the commit, and CI catches commits made without hooks.
- The index needs no hand edits, and renumbering an ADR fails until every reference
  follows.
- Every commit pays about 0.15 seconds for the reference hook; a commit that changes
  ADRs pays about 0.7 seconds, most of it for the scan of the tree.
- A new field, status or tag means changing the writing style and the script in the
  same pull request.
- The epic layout is enforced, not just written down: a directory means an epic has
  supporting files, so the listing stays readable as epics accumulate.
- The template is checked for its headings only, since its values are placeholders.

### Alternatives

- **markdownlint with a frontmatter schema.** Checks one file at a time, so supersession
  and references stay unchecked, and it brings the npm toolchain into Python-side docs.
- **A JSON Schema check of the frontmatter alone.** Covers the fields, not the headings,
  the index or references.
- **One hook checking everything on every commit.** Simpler, but the scan of the tree
  would cost every commit about 0.7 seconds, mostly for commits that touch no ADR.
- **The check in CI only.** Finds a stale index after the push, and the cost of running
  it locally is small.
- **adr-tools or log4brains.** Each brings its own file format and commands, and neither
  checks references from outside the ADR directory.
- **A separate checker per document kind.** Two scripts and four hooks for one set of
  rules about names, links and generated indexes; the cost is one file, not two.
