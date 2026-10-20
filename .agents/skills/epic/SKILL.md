---
name: epic
description: Write a new epic specification in docs/epics/. Use when asked to draft, plan or name an epic.
disable-model-invocation: true
---

# Epic specifications

The rules are in [docs/epics/README.md](../../../docs/epics/README.md) and the [writing style](../../../docs/style.md), and `just docs-check` checks names, headings and the index.
Read the README's "Structure and Conventions" and "Writing an epic" first; this skill gives only the order of the steps and the traps.

## Before writing

- **Only new epics.**
  A specification records the plan as the epic started and is not updated afterwards.
  Asked to change a started epic, say so and propose an ADR or a code change instead.
  Marking an epic completed is a change to the README's lists, not to the epic; "The Saga so far" says how.
- **Pick the type** and start from its template: `docs/epics/epic-template-exploratory/README.md` or `docs/epics/epic-template-implementation/README.md`.
  For an `Exploration and Implementation Epic`, start from the implementation template and add the exploration sections the work needs.
- **Pick the code name:** an animal in neither list of "The Saga so far".
  Offer the user two or three; the team chooses.

## Steps

1. Take the next free number: the highest `epic-NNNN` in `docs/epics/` plus one (`fd '^epic-[0-9]{4}' docs/epics -d1 | sort | tail -1`).
   Look for a number an open PR already takes: `gh pr list --state open --json number,files --jq '.[] | .number as $n | .files[].path | select(startswith("docs/epics/epic-")) | "\($n) \(.)"'`.
2. Create `docs/epics/epic-NNNN-<code-name>.md`, the code name in kebab-case.
   Drop the template's example image; only an epic with files of its own becomes a directory, as the README says.
3. Keep the template's heading line and `**Epic Type:**` line, with the title, the code name and the type filled in.
4. Replace every `<…>` and keep the template's sections.
5. Run `just docs-check`, never `uv` directly.
   It adds the epic to "Unfolding epics" in `docs/epics/README.md`; commit that change with the epic.

## Traps

- No confidential content, as the template says: the repo is public.
- Keep implementation detail to what the team needs to plan tasks; the decisions that outlive the epic go into an ADR.
