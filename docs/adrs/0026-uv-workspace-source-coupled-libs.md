# ADR-0026 — `uv` workspace with source-coupled internal libraries

- **Status:** accepted
- **Date:** 2026-06-30

## Summary

In the context of **services, libraries and tools that depend on each other and are
developed in one repository**

facing **internal libraries consumed as PyPI versions, which let services drift onto
incompatible versions of them**

we decided for **one `uv` workspace with one `uv.lock`, internal libraries consumed from
source, and one tested Python range for the published libraries**

and neglected **pinned PyPI versions inside the repo, a single root `pyproject.toml`,
and consuming only some libraries from source**

to achieve **a HEAD at which every member works with the current version of every
other**

accepting that **a breaking library change must fix all its consumers in the same pull
request, and published libraries need a second test surface**.

## Details

### Context

Services depended on internal libraries through PyPI version constraints, which allowed
skew: `ghga-event-schemas` was required at `~=12` and `~=13` at the same time, and
`ghga-datasteward-kit` required `ghga-transpiler <3` while the transpiler was at 3.0.0.
`file-services-backend` had already shown that one lock file with `uv` works. Published
libraries supported a broad Python range, while services target 3.13.

### Decision

- The repo is one **`uv` workspace**. Each library, service and tool is a member with
  its own `pyproject.toml` and its own version.
- Internal libraries are consumed **from source** through `[tool.uv.sources]` (`hexkit =
  { workspace = true }`). There is **one `uv.lock`**, so every package has exactly one
  resolved version across the repo.
- The workspace baseline is **Python 3.13**.
- The published libraries and CLIs share one `requires-python` floor, currently 3.11,
  and are tested standalone across 3.11 to 3.14 against dependencies resolved from PyPI
  ([ADR-0027](0027-versioning-and-release-by-tag.md)).

### Consequences

- There is no version skew at HEAD, by construction.
- A breaking change to a shared library is fixed for all consumers in the same pull
  request; library upgrades cannot be deferred.
- A library's independent lifecycle means its own release cadence, not consumers lagging
  behind.
- Each published library has two test surfaces: the workspace lock and the standalone
  matrix.
- One version of each third-party dependency for the whole repo forces keeping it
  current.

### Alternatives

- **Pinned PyPI versions inside the repo.** Reproduces the skew in one repository.
- **One root `pyproject.toml`**, as in `file-services-backend`. Workable, but loses each
  member's own dependency declarations.
- **Some libraries from source, others pinned.** Partial integration, with the
  complexity of both.
- **A Python floor per published member.** Ranges that no test verifies.
