---
status: accepted
date: 2026-09-09
tags: [docs, release]
related: [ADR-0025, ADR-0033, ADR-0038]
---

# ADR-0039 — One documentation site for the monorepo

## Summary

In the context of **hexkit's documentation site, whose repository was to be archived and
whose URL is in published PyPI metadata**

facing **a monorepo with no docs lane, in which the imported docs no longer built**

we decided for **one GitHub Pages site with a subpath per documented member, found by
its `great-docs.yml`, built from `main` in its own environment, with redirects at the
old URL**

and neglected **retiring the site, keeping the hexkit repository as docs host, versioned
docs, and the workspace environment**

to achieve **documentation that outlives the old repositories and takes further members
without another decision**

accepting that **the docs URL changes, two upstream workarounds are ours to carry, and
every push to `main` rebuilds the whole site**.

## Details

### Context

`hexkit` is the only member with a documentation site: a 42-page user guide and an API
reference, built with great-docs and published from its own repository. Archiving that
repository disables its Actions while GitHub keeps serving the Pages site as it stands.
The URL is also in the immutable PyPI metadata of `hexkit` 9.0.0 and 9.0.1.

The import stripped the build hooks the docs need
([ADR-0025](adr-0025-consolidate-into-monorepo.md)), so they did not build in the
monorepo.

### Decision

- **One site**, `ghga-de.github.io/ghga`, with a subpath per documented member
  (`/ghga/hexkit/`) and an index at the root. GitHub serves one Pages site per
  repository.
- **A member is documented if it has a `great-docs.yml`.** The build needs that file
  anyway, so a `[tool.ghga]` marker
  ([ADR-0033](adr-0033-capability-markers-and-placement.md)) would be a second source
  that could disagree. `scripts/docs_members.py` finds the members for both the workflow
  and `just docs`.
- **The site tracks `main`**, the released state
  ([ADR-0038](adr-0038-branching-strategy.md)). Building from `dev` would put unreleased
  API behind PyPI's documentation link.
- **The toolchain has its own `.venv-docs`**, from a `docs` dependency group in the root
  `uv.lock`. Quarto comes from a devcontainer feature and a CI setup step.
- **The old URL redirects** into the new site, published before the hexkit repository
  was archived.

### Consequences

- The docs URL changes. `hexkit`'s metadata and README name the new one; the redirects
  cover the versions already on PyPI.
- great-docs needs the deploy subpath in two settings, and `docs_members.py --check`
  fails the lane when they disagree.
- Two workarounds for great-docs bugs stay as build hooks in `libs/hexkit/scripts/`
  until fixed upstream.
- Contributors need `just docs-install` once, and Quarto in the devcontainer.
- Every push to `main` rebuilds the whole site, about two minutes per member. A path
  filter would duplicate the member discovery.

### Alternatives

- **Retire the site.** The user guide is hand-written and cannot be regenerated from
  code.
- **Keep the hexkit repository as docs host.** Contradicts its retirement and looks
  maintained.
- **A custom domain.** Deferred: a DNS decision on top of this site, not needed now.
- **Versioned docs.** Couples the docs lane to the PyPI lane, while `main` already is
  the released state.
- **The `docs` group in the workspace environment.** Makes `just sync-check`, and with
  it `just test`, fail.
