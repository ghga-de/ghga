# ADR-0021 — One Pages site for the monorepo, one subpath per documented member

- **Status:** Proposed
- **Date:** 2026-09-09
- **Deciders:** Christoph Zwerschke

## Context
`hexkit` is the only member with a documentation site: a hand-written user guide (42 Quarto
pages — architecture concepts, protocols, per-provider guides, observability, glossary) plus
an API reference generated from docstrings by [great-docs](https://posit-dev.github.io/great-docs/).
Upstream published it to `ghga-de.github.io/hexkit` from its own `publish_docs.yml` on every
push to `main`.

That repo is about to be archived ([runbook §7](../migration/runbook.md)), and archiving
disables Actions while GitHub keeps serving the existing Pages site. Whatever stands at that
URL when we archive stands there permanently. The URL is not ours to retire either: it is
baked into the immutable PyPI metadata of `hexkit` 9.0.0 and 9.0.1 (`Documentation =`) and
into the README rendered on their PyPI pages.

The monorepo has no docs lane at all, and the import made the existing config unbuildable:
`great-docs.yml` registers two `pre_render` hooks under `scripts/`, which
`drop_paths_for_kind` strips for every `lib`/`service`/`tool` row
([ADR-0010](0010-history-preserving-migration.md)). So the decision cannot be deferred by
"leave it as it is" — as imported, hexkit's docs do not build here.

## Decision
We will publish documentation from the monorepo as **one GitHub Pages site**,
`ghga-de.github.io/ghga`, with **one subpath per documented member** (`/ghga/hexkit/`) and a
plain index at the root listing them. GitHub serves one Pages site per repository, so the
subpath is what makes the site extensible to `schemapack`, `metldata` or the CLIs without a
second decision.

**A member is documented iff it carries a `great-docs.yml`.** That file is the build's own
config and has to exist anyway, so presence is the marker. This deviates from
[ADR-0014](0014-capability-markers-and-placement.md), which declares capability in
`[tool.ghga]`: a marker here would be a second source of truth able to disagree with the
config it describes. `scripts/docs_members.py` is the discovery, read by both the workflow's
matrix and `just docs`, so a local build cannot drift from the deployed one
([ADR-0015](0015-task-runner.md)).

**The site tracks `main` only.** `main` is the released state
([ADR-0020](0020-branching-strategy.md)); publishing from the integration branch would put
unreleased API on the URL that PyPI's `Documentation` link points at.

**The toolchain lives in its own `.venv-docs`,** resolved from the single root `uv.lock` via
a `docs` dependency group. great-docs pulls ~450 MB (Jupyter, IPython, Quarto plumbing) that
no test needs, and installing it into the workspace venv makes `just sync-check` — and
therefore `just test` — report the environment as not matching the lock. `.venv-testbed` is
the same pattern. Quarto itself is a standalone binary, not a Python package, so it comes
from a devcontainer feature and a `quarto-actions/setup` step.

**Before the hexkit repo is archived, we will publish a final build at
`ghga-de.github.io/hexkit`** so the URL in the shipped PyPI metadata keeps resolving. The
path structure is preserved under the new prefix, so that build can be a mirrored tree of
redirect stubs; the alternative is the real docs plus a "moved" banner, frozen. That choice
is open — but it has to be made *before* archiving, because afterwards the URL cannot be
changed.

## Consequences
- The docs URL changes. `libs/hexkit`'s `Documentation` metadata, its README links and
  `great-docs.yml` now name the new location; the shipped 9.0.0/9.0.1 metadata cannot be
  amended and is covered by the final redirect build instead.
- Two `great-docs.yml` keys must agree with the deploy subpath, and great-docs reads them in
  different places: `site_url` drives link and asset resolution, while the SEO pass reads
  `seo.canonical.base_url` and, unset, guesses `https://<owner>.github.io/<repo>/` — which in
  a monorepo silently drops the member subpath. `docs_members.py --check` asserts both, and
  the lane fails on a mismatch rather than publishing wrong canonical links and sitemaps.
- Two upstream great-docs workarounds stay as `pre_render` hooks under
  `libs/hexkit/scripts/`. `add_member_anchor_ids.py` supplies the qualified anchors
  great-docs promises in `objects.json` but does not emit. `fix_source_link_paths.py`
  supplies the member prefix on "view source" URLs; great-docs' advertised `source.path`
  monorepo override does not help, because it builds the URL as `<source.path>/<basename>`
  and discards the package subdirectories. Both carry a TODO to drop them when fixed
  upstream.
- Contributors need one more one-time step (`just docs-install`) and a devcontainer rebuild
  for Quarto. `just docs` fails with instructions when either is missing.
- Every push to `main` rebuilds and redeploys the whole site (~2 minutes per member). There
  is no `paths:` filter: an accurate one would have to enumerate each documented member's
  tree, duplicating the list the discovery script exists to own.

## Alternatives considered
- **Retire the docs site.** Rejected: the user guide is 42 hand-written pages, not
  regenerable from code, and it is the only prose documentation hexkit has.
- **Keep the `hexkit` repo unarchived as a docs host,** pushed to from the monorepo.
  Rejected: it contradicts the retirement, and leaves a repo that looks maintained.
- **A custom domain (`docs.ghga.de`).** Not rejected — deferred. It is a CNAME on top of
  this Pages site and needs a DNS decision we do not need to make now.
- **Per-release (versioned) docs** instead of tracking `main`. Rejected for now: great-docs
  supports it, but it couples the docs lane to the PyPI lane for a site that has always
  tracked the branch, and `main` is already the released state.
- **Installing the `docs` group into the workspace venv.** Rejected: verified to break
  `just sync-check`, which gates `just test`.
