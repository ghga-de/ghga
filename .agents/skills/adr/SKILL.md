---
name: adr
description: Write, amend or supersede an architecture decision record in docs/adrs/. Use when asked to record a decision, or to draft, change or replace an ADR.
---

# Architecture decision records

The rules are in the [ADR section of the writing style](../../../docs/style.md#architecture-decision-records), and `just docs-check` checks them.
Read that section first; this skill gives only the order of the steps and the traps the check does not catch.

## New ADR

1. Take the next free number: the highest `docs/adrs/adr-NNNN-*.md` plus one (`fd '^adr-[0-9]{4}' docs/adrs | sort | tail -1`).
   The check sees only your branch, so look for a number an open PR already takes: `gh pr list --state open --json number,files --jq '.[] | .number as $n | .files[].path | select(startswith("docs/adrs/adr-")) | "\($n) \(.)"'`.
2. Copy `docs/adrs/adr-template.md` to `docs/adrs/adr-NNNN-kebab-case-title.md`, fill every `{…}` and delete the template's comments.
3. Set `status: proposed` and today's date while the PR is in review, even when the team has already agreed.
   Take tags only from the style guide's list, and add `supersedes` or `related` only when they have a value.
4. Write the Summary last, to the lengths in the style guide's table.
5. Run `just docs-check`, never `uv` directly.
   It regenerates the index in `docs/README.md`; commit that change with the ADR.
6. Before the PR merges, set `status: accepted` and the date of acceptance.

## Change an existing ADR

Decide first which of three it is, and say so in the PR description:

- **Clarify:** the decision stays as it was, and the edit only explains it better.
  Edit the passage directly, with no `amended` field and no marker.
- **Amend:** part of the decision changes, but the decision stands.
  Set `amended` to today and add a paragraph starting `**Amended YYYY-MM-DD:**` at the passage it affects.
- **Supersede:** the change replaces the decision.
  Write a new ADR with `supersedes: [ADR-XXXX]`, and in the old one set `status: superseded` and `superseded-by: [ADR-NNNN]`, both in the same PR.

Then run `just docs-check`.

## Traps

- Change only the passages the task needs; rewording the rest of an existing ADR buries the change.
- ADRs 0001 to 0024 came from the old ADR repository: edit them lightly and keep their length and voice, since the 500-word target is for the later ones.
- An ADR records the decision, not its rollout: checklists go in the PR or a runbook.
- A new tag needs the style guide's tag list and `TAGS` in `scripts/docs_check.py` extended first.
