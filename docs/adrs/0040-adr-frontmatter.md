# ADR-0040 — YAML frontmatter for ADRs

- **Status:** proposed
- **Date:** 2026-09-15

## Summary

In the context of **39 ADRs in `docs/adrs/`, indexed by a hand-maintained table in
`docs/README.md`**

facing **an index that drifts from the files, and status, supersession and topic that
only prose and a Markdown list carry**

we decided for **YAML frontmatter that replaces the header list, with the index table
generated from it**

and neglected **keeping the header list, frontmatter next to the header list, and
repeating the number and title in the frontmatter**

to achieve **one machine-readable source per fact, an index that cannot drift, and ADRs
findable by topic**

accepting that **every ADR header is rewritten once, the index shows titles instead of
short descriptions, and the tag list needs keeping up**.

## Details

### Context

Each ADR carries its status, dates and supersession in a bulleted header list, and
`docs/README.md` repeats number, title and status in a table kept by hand. That table
has gone stale more than once, and its link texts have drifted from the titles. Links
between ADRs exist only in prose, and nothing groups ADRs by topic. With backend,
front-end and platform decisions in one directory, a reader has to open files to find the
relevant ones.

The header list was designed to map one to one onto frontmatter
([writing style](../style.md#header-fields-and-status)). GitHub renders frontmatter as a
table above the document, so it can replace the list without hiding the fields.

### Decision

Every ADR, the template included, starts with a YAML frontmatter block, and the header
list goes. For ADR-0027:

```yaml
---
status: accepted
date: 2026-06-30
supersedes: [ADR-0024]
tags: [release, deploy]
related: [ADR-0026, ADR-0033, ADR-0038]
---
```

- **`status`** and **`date`** are required; their values are the ones in the writing
  style.
- **`amended`**, **`supersedes`**, **`superseded-by`** and **`related`** are present
  only when they have a value. ADRs are named `ADR-NNNN`, as in prose.
- **`tags`** is required, one or more from a list kept in the writing style. The first
  list is `backend`, `frontend`, `data`, `events`, `security`, `build`, `release`,
  `deploy`, `testing`, `docs` and `process`.
- **The number and title are not repeated.** They stay in the file name and the
  `# ADR-NNNN — Title` heading.
- **The index table in `docs/README.md` is generated** between marker comments, with
  number, title, status, supersession and tags. Like other generated artifacts it is
  regenerated, never edited by hand.

How the fields and the index are checked is a separate decision, taken in the ADR on ADR
linting.

### Consequences

- Status and supersession live in one place, and the index follows from them.
- ADRs can be listed by tag and by status without reading the prose.
- One pull request rewrites the header of every ADR and the writing style. This touches
  ADRs 0001 to 0024 only in their header, so they keep their original text.
- The index loses its hand-written short descriptions in favour of the titles; titles
  that do not work in the index get rewritten instead.
- A new topic means extending the tag list in the writing style first.

### Alternatives

- **Keep the header list and parse it.** Works, but a Markdown list is a format we would
  define and parse ourselves, and it has no place for tags or related ADRs that reads
  well.
- **Frontmatter next to the header list.** GitHub would show every field twice, and the
  two could disagree.
- **`id` and `title` in the frontmatter.** Both already have a source that people see;
  a copy only adds a mismatch for the lint to catch.
- **Free-form tags.** Near-duplicates (`ci`, `build`, `pipeline`) would split the topics
  the tags are for.
