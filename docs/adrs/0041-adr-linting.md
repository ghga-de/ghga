# ADR-0041 — A pre-commit check for ADRs

- **Status:** proposed
- **Date:** 2026-09-15

## Summary

In the context of **ADRs with YAML frontmatter and a generated index
([ADR-0040](0040-adr-frontmatter.md))**

facing **rules for fields, headings and references that only review enforces, and ADR
references across the tree that break when files move**

we decided for **one repo-local pre-commit hook running a script in `scripts/`, which
checks the whole ADR set and every ADR reference on each commit and regenerates the
index**

and neglected **markdownlint with a frontmatter schema, a schema check alone, a CI-only
check, and ADR tools with their own format**

to achieve **ADRs that follow the template, an index and references that cannot go
stale, and the same result locally and in CI**

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
whole tree ([ADR-0036](0036-pre-commit-hooks.md)).

### Decision

A script in `scripts/` checks the ADRs; a `repo: local` hook runs it through `uv run`,
and a `just` recipe runs it by hand. It always checks the whole set, since most rules
span files, and it runs on every commit, since a reference to an ADR can be added in any
file.

It fails when:

- **The file name** is not `NNNN-kebab-case.md`, a number is taken twice, or the heading
  is not `# ADR-NNNN — Title` with the number from the file name.
- **The frontmatter** lacks a required field, has an unknown one, or has a status, date
  or tag outside the values in the writing style.
- **The headings** `Summary`, `Details`, `Context`, `Decision`, `Consequences` and
  `Alternatives` are missing or out of order.
- **Supersession** is one-sided: `superseded-by` needs status `superseded` and a
  matching `supersedes` in the other ADR, and the reverse.
- **A reference dangles:** an `ADR-NNNN` mention, including compound forms such as
  `ADR-0028/0035`, or a link into `docs/adrs/`, in any tracked text file, names an ADR
  that does not exist.

It also regenerates the index in `docs/README.md` and fails when that changed the file,
as the whitespace fixers do, so the fix is to stage the result.

The script has unit tests in `scripts/tests/`. Prose rules, such as length and the
wording of the Summary, stay with review.

### Consequences

- A broken ADR or reference fails the commit, and CI catches commits made without hooks.
- The index needs no hand edits, and renumbering an ADR fails until every reference
  follows.
- The hook adds about a second to every commit, since it scans the tree.
- A new field, status or tag means changing the writing style and the script in the
  same pull request.
- Epics are checked only for their ADR references. If their format gets standardised,
  the same hook can check it.
- The template is checked for its headings only, since its values are placeholders.
### Alternatives

- **markdownlint with a frontmatter schema.** Checks one file at a time, so supersession
  and references stay unchecked, and it brings the npm toolchain into Python-side docs.
- **A JSON Schema check of the frontmatter alone.** Covers the fields, not the headings,
  the index or references.
- **The check in CI only.** Finds a stale index after the push, and the cost of running
  it locally is small.
- **adr-tools or log4brains.** Each brings its own file format and commands, and neither
  checks references from outside the ADR directory.
