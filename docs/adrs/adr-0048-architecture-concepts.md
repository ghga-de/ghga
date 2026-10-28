---
status: accepted
date: 2026-10-23
tags: [docs, process]
related: [ADR-0040, ADR-0041]
---

# ADR-0048 — Numbered architecture concepts with frontmatter

## Summary

In the context of **seven architecture concepts (AC001 to AC007) moving from the internal documentation site into `docs/architecture/`, next to four unnumbered architecture documents**

facing **two naming schemes in one directory, links in epics that point at the old site, and no list of what the directory holds**

we decided for **one numbered set, `ac-NNNN-kebab-case.md` with the ADR frontmatter and statuses of its own, indexed in a generated `docs/architecture/README.md` and checked by `scripts/docs_check.py`**

and neglected **keeping the old names, unnumbered documents with a hand-kept list, the overview as the index, and folding the concepts into the ADRs**

to achieve **concepts that are cited as `AC-NNNN` the way ADRs are, an index that cannot drift, and references that fail when a concept moves**

accepting that **the four existing documents get new names and every link to them changes once, and the check grows a third set**.

## Details

### Context

The internal documentation site held the architecture concepts as `ac001_file_transfer_and_storage.md` and so on, cited as AC001 to AC007 in epics and SOPs.
It rendered them with MkDocs extensions and a glossary hook that GitHub does not know.
`docs/architecture/` already held the monorepo overview, the metadata and file journeys, the Kafka cascades map and the MongoDB migrations page, under free names.

ADRs and epics have a numbered name, a checked shape and a generated index ([ADR-0040](adr-0040-adr-frontmatter.md), [ADR-0041](adr-0041-docs-linting.md)).
A concept differs from both: it describes how something works and is kept current, where an ADR records one decision and an epic a plan.

### Decision

- **Names.**
  Each concept is `docs/architecture/ac-NNNN-kebab-case.md`, titled `# AC-NNNN — Title` and cited as `AC-NNNN`.
  The imported concepts keep their numbers, 1 to 7.
  The monorepo overview takes 0, the number epics give their first entry, and the other three follow from 8 in the order they were written.
- **Frontmatter.**
  `status`, `date` and `tags` are required; `amended` and `related` are present only when they have a value.
  The tags are the ADR tags, and `related` names ADRs and concepts.
  The statuses are `draft`, `current` and `outdated`, since a concept is not accepted but kept in step with the system.
  No supersession: a concept that no longer holds is rewritten, or marked `outdated` until it is.
- **Index.**
  `docs/architecture/README.md` explains what a concept is, points newcomers to AC-0000, AC-0008 and AC-0009, and holds the index table between `ac-index` markers.
  The overview stays a narrative document of its own.
- **Checks.**
  `scripts/docs_check.py` checks names, titles and frontmatter, reports dangling `AC-NNNN` mentions and links anywhere in the tree, and regenerates the index, in the hooks that already run for ADRs and epics.
- **Rendering.**
  Concepts are GitHub Flavored Markdown: Mermaid fences, GitHub alerts and `<img width>` replace the MkDocs extensions, and glossary markup becomes plain text.
  Images sit in a shared `images/` directory, named after their concept.

### Consequences

- A concept is cited and linked like an ADR, and the check catches a stale link.
- The index lists every concept with its status, so an outdated concept is visible without opening it.
- Every link to the four existing documents changed once, in this change.
- A new status means changing the README and `AC_STATUSES` in the script together.

### Alternatives

- **Keep the old names (`ac001_…`) beside the unnumbered documents.**
  Two schemes in one directory, and neither matches the ADRs and epics.
- **Unnumbered documents with a hand-kept list.**
  The lists in `docs/README.md` already drifted before the ADR index was generated.
- **The overview as the index.**
  The overview describes the repository and its build; a generated table at its head would give one page two owners, a person and the script.
- **Concepts as ADRs.**
  An ADR is not updated as the system changes, and the concepts must be.
