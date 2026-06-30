# ADR-0003 — Repository scope: everything except `datahub-test-bed`

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Leon Kuchenbecker

## Context
Given source-coupled libraries ([ADR-0002](0002-uv-workspace-source-coupled-libs.md)), anything
a deployed service imports at HEAD **must** live in the workspace — otherwise the service would
consume it as a pinned PyPI version, reintroducing skew. That already pulls in all the
libraries. The genuine discretion is only over the *leaves* nothing in the cluster imports:
the external CLIs (`ghga-connector`, `ghga-datasteward-kit`), `ghga-validator`, and the
data-hub self-check tool (`datahub-test-bed`).

The external CLIs are already **integration-test actors** in `archive-test-bed` (the kit drives
uploads, the connector drives downloads) and depend on internal libs.

## Decision
Import **all repositories except `datahub-test-bed`**. Also exclude the retired
`microservice-repository-template` ([ADR-0001](0001-consolidate-into-monorepo.md)).
- Libraries → `libs/`; services → `services/`; CLIs/jobs → `tools/`; front end →
  `frontend/`; the BDD suite → `testbed/`.
- `ghga-connector` and `ghga-datasteward-kit` come **in**: they are part of the integration
  surface and depend on internal libs, so in-repo keeps them skew-free and tested against HEAD.
- `datahub-test-bed` stays its own repo: different audience (data hubs verifying *their own* S3
  setup), zero coupling to the cluster.

The full mapping is [scripts/migration/repos.tsv](../../scripts/migration/repos.tsv).

## Consequences
- Externally-consumed libs/CLIs are released from the monorepo via per-component tags
  ([ADR-0004](0004-versioning-and-release-by-tag.md)); their PyPI lifecycle stays independent.
- The CLIs you ship always match the services you deploy (tested together in the test bed).
- `datahub-test-bed` continues to depend on published artifacts (its data-hub users want
  released versions anyway).

## Alternatives considered
- **Everything including `datahub-test-bed`.** Rejected: different audience, no coupling.
- **Deployable system only (libs/CLIs stay external).** Rejected: contradicts
  [ADR-0002](0002-uv-workspace-source-coupled-libs.md) for the libraries and drops the CLIs out
  of HEAD integration testing.
