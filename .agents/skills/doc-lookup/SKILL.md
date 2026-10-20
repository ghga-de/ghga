---
name: doc-lookup
description: Find the passage in the repo docs that answers a question about a design decision, a convention, a release or migration step, or how a service or flow behaves. Use before changing behaviour you do not know, or when asked "which ADR", "why" or "how does X flow".
# User-invoked: an eval showed no gain over a session without it
# (docs/agent-instructions.md#admitting-a-skill).
disable-model-invocation: true
---

# Look up the docs

1. Pick the shelf by the kind of question, and search it first:
   - why, or which decision: `docs/adrs/`; the index in `docs/README.md` gives each ADR's status and tags
   - current flows and components: `docs/architecture/`
   - how we work: `docs/conventions.md`, `docs/style.md`, `docs/releases.md`, `docs/dependencies.md`
   - a service's configuration, API or events: `services/<name>/README.md` and its `config_schema.json`, never `deploy/charts/*/README.md`, which is generated
   - plans: `docs/epics/`, where the README's lists say which epics are completed and which are unfolding; a specification is frozen when its epic starts, so it never says how something works now
2. Search narrowly, with `rg -il '<term>' <shelf>`, under both the abbreviation and the full name.
   A service's directory is often its abbreviation (`ucs`, `dcs`, `ifrs`) and its README title the full name; the architecture docs also write RS, WPS, DINS, DHFS, ARS and RTS.
3. In a file over about 10 KB, list the headings first (`rg -n '^#{1,4} ' <file>`), then read only the section you need.
4. If an ADR is superseded, follow `superseded-by` for the answer, and read the ADRs in `related`.
5. Confirm a claim in the code by its symbol name (`rg -n 'def name|class Name'`), not by a line number a doc gives.
6. After two shelves and two phrasings without a hit, answer "not in the docs" and say where it might live.
   Do not fill the gap from an epic.
