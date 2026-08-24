# ADR-0002 — `uv` workspace with source-coupled internal libraries

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
We want "HEAD of `main` is always fully integrated" and "make use of `uv` as much as possible".

Today services depend on internal libraries via **published PyPI version constraints**, which
allows skew: `ghga-event-schemas` is pinned at both `~=12` and `~=13` across services;
`ghga-datasteward-kit` pins `ghga-transpiler >=2.1.2,<3` while transpiler is already `3.0.0`
(unsatisfiable against HEAD). `file-services-backend` already uses `uv pip compile` with a
single global lock, proving uv at smaller scale.

Internal libraries (`hexkit`, `ghga-service-commons`, `ghga-event-schemas`, `schemapack`,
`metldata`) are also published to PyPI for **external** consumers and support a broad Python
range (3.9–3.12), whereas services target 3.13.

## Decision
The repo is a single **`uv` workspace**. Each lib/service/tool is a member with its own
`pyproject.toml` and **its own version**. Internal libraries are consumed **from source** via
`[tool.uv.sources]` (`hexkit = { workspace = true }`, …). There is **one `uv.lock`**, so
exactly one resolved version of every package exists across the whole repo.

- **Workspace Python baseline = 3.13.**
- Published libraries keep **broad dependency ranges** in their own `pyproject.toml`; a
  **per-package standalone matrix** (`uv run --python 3.10…3.13`) validates the *published*
  combination separately from the workspace lock.

**Amended 2026-08-24 — common `>=3.11` floor across the PyPI lane.** Every lane member now
declares `requires-python = ">=3.11"` and carries matching classifiers, and the matrix runs
**3.11–3.14** (`TEST_PYTHONS` in `scripts/pypi_members.py`), superseding the `3.10…3.13`
above. This narrows what external consumers get — `hexkit`, `ghga-service-commons` and
`ghga-connector` drop 3.10; `ghga-transpiler` and `ghga-validator` drop 3.9 and 3.10 — in
exchange for one range the whole lane is actually tested against, rather than per-member
floors that no surface verified. It also trades away part of the "broad range" premise
above: the range is now uniform rather than per-library. The floors live in the members'
own `pyproject.toml`, so for members still synced from mainline ([ADR-0010](0010-history-preserving-migration.md))
this is a divergence that conflicts until the same change is made upstream.

## Consequences
- Integration is structural: there is no version skew possible at HEAD.
- **A breaking change to a shared lib must be fixed for all consumers in the same PR.** This is
  a deliberate change to how teams work (no deferred lib upgrades).
- "Independent lifecycle" of a library means independent **release cadence**
  ([ADR-0004](0004-versioning-and-release-by-tag.md)), not consumers lagging behind.
- Two test surfaces per lib: the workspace lock ("integrated combo") and the matrix
  ("published combo"). Both are required; CI cost rises modestly.
- A single `uv.lock` pins one version of each third-party dep for the whole repo — a strong
  forcing function for keeping everything current.

## Alternatives considered
- **Pinned PyPI versions inside the repo (status quo).** Rejected: reproduces today's skew in
  one repo; HEAD would not be integrated.
- **`file-services-backend`'s single-root-pyproject model.** Workable but collapses per-member
  dependency declarations; the uv workspace is the more scalable, uv-native form.
- **Hybrid (some libs source, some pinned).** Rejected: partial integration; complexity with
  little benefit once we accept lockstep lib upgrades.
