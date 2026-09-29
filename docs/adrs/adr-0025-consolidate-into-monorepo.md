---
status: accepted
date: 2026-06-30
tags: [process, build]
related: [ADR-0026]
---

# ADR-0025 — Consolidate into one monorepo by history-preserving import

## Summary

In the context of **about 30 GHGA repositories, most of them kept in line by syncing
files from a template repository**

facing **toolchain changes that had to reach 25 repositories, cross-cutting changes that
were never atomic, and no single place where all of GHGA was tested together**

we decided for **one monorepo at `ghga-de/ghga` holding everything except
`datahub-test-bed`, imported with its history and synced one way until each old
repository is retired**

and neglected **keeping the template sync, a polyrepo build tool, a one-time snapshot, a
bidirectional mirror and `git subtree`**

to achieve **one toolchain defined once, cross-cutting changes in one pull request, and
the full history in `git log` and `git blame`**

accepting that **commit SHAs change, old `#NNN` references dangle, and a member's own
files stay aligned with its old repository while that one still syncs**.

## Details

### Context

GHGA maintained about 30 repositories. About 25 were generated from
`microservice-repository-template` and kept consistent by a `.template/` file sync with
a CI check in each repository. Every toolchain change had to reach all of them, a new
`ghga-event-schemas` major spanned many pull requests, and nothing built and tested all
of GHGA together; the version skew between services showed it. `file-services-backend`
had already shown that a GHGA Python monorepo works.

The old repositories kept receiving commits while the monorepo was built, so the move
could not be a single cut.

### Decision

We consolidate the GHGA services, libraries, CLIs, front end and test bed into one
polyglot monorepo at `github.com/ghga-de/ghga`, and retire the template and its sync.
The toolchain is defined once, at the root.

**Scope.** Every repository comes in except `datahub-test-bed` and the retired template.
The libraries have to, since services consume them from source
([ADR-0026](adr-0026-uv-workspace-source-coupled-libs.md)). The external CLIs
`ghga-connector` and `ghga-datasteward-kit` come in as well: they depend on internal
libraries and drive the test bed, so they are tested against HEAD. Documentation
repositories such as the epic specifications come in as the design record of the code.
`datahub-test-bed` stays out: it serves data hubs checking their own storage and has no
coupling to the platform.

**Import.** `git filter-repo` rewrites each repository into its directory and drops the
boilerplate the root now provides. Historical release tags are not imported.

**Sync.** Until an old repository is retired, we re-run the import and merge only its
new commits; `filter-repo` gives the same SHAs for the same append-only history. To keep
those merges free of conflicts, harmonisation happens at the root, and a synced member's
`src/` and own `pyproject.toml` stay aligned with its old repository. A repository is
retired, archived and dropped from the manifest once it is verified fully synced.

The [manifest](../../scripts/migration/repos.tsv) holds the mapping and the retired
repositories; the [runbook](../migration/runbook.md) holds the steps.

### Consequences

- Cross-cutting changes land in one pull request and are tested together; the template
  machinery and its per-repository checks are gone.
- History, authorship and dates survive, and `git blame` and `git log` follow files into
  their new paths.
- Commit SHAs change, so `#NNN` references in old commit messages dangle. The originals
  stay on `ghga-de`.
- While a repository still syncs, a change to its member's own `pyproject.toml`
  conflicts until it is made there too.
- The released CLIs match the services they are tested with. `datahub-test-bed` keeps
  using published versions.
- The repository is large; affected-target CI keeps builds and tests scoped.

### Alternatives

- **Keep the template sync.** It is the maintenance burden we want gone, and it cannot
  make integration atomic.
- **A polyrepo with a build tool such as Bazel across repositories.** Heavier, and still
  no single integrated HEAD.
- **Import only the deployed system.** Contradicts source-coupled libraries and leaves
  the CLIs out of integration testing.
- **A one-time snapshot, then diverge.** The catch-up cost grows with every commit to
  the old repositories.
- **A bidirectional mirror with josh.** Too much for a temporary window.
- **`git subtree`.** Has incremental pulls built in, but gives messier history and worse
  blame across the import boundary.
