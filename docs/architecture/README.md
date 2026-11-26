# Architecture concepts

An architecture concept describes how a part of GHGA works or is built, and why: the mechanism across services, libraries or the repository, with the diagrams that show it.
It differs from an [ADR](../adrs/), which records one decision and stays as it was taken, and from an [epic](../epics/README.md), which records a plan before the work starts.
A concept is kept current: when the system it describes changes, the concept changes with it.

## Start here

- **[AC-0000](ac-0000-monorepo-overview.md)** is the overview of the monorepo: its layout, the `uv` workspace, versioning, Helm charts, the test bed and CI/CD.
- **[AC-0008](ac-0008-metadata-and-file-journeys.md)** follows metadata and files through the services as built today; read it before touching submission, accession, upload, file mapping or metadata serving.
- **[AC-0009](ac-0009-kafka-cascade-map.md)** draws the same flows as Kafka event cascades, in the interactive [kafka-cascade-map.html](kafka-cascade-map.html).

## Writing an architecture concept

The audience is GHGA developers and coding agents.
Follow the [writing style](../style.md); what follows is what is specific to a concept.

- **Name** the file `ac-NNNN-kebab-case-title.md`, with the next free number, directly in this directory.
- **Title** it `# AC-NNNN — <Title>`, in sentence case, right after the frontmatter.
- **Refer** to a concept as `AC-NNNN` in prose, as with ADRs.
- **Put images** in [`images/`](images/), named after the concept they belong to (`ac-0006-dlq-flow.png`).
  Prefer a Mermaid diagram where it can show the same, since it changes with the text.
- **Size an image** with an `<img>` tag and its `width` attribute; GitHub ignores attribute lists such as `{width="400px"}`.
- **Use GitHub alerts** (`> [!NOTE]`) for notes and warnings.

### Header fields and status

Every concept starts with a YAML frontmatter block, in this field order:

| Field | Value |
|---|---|
| `status` | One word from the list below. Always present. |
| `date` | `YYYY-MM-DD` the concept was first written. Always present. |
| `amended` | `YYYY-MM-DD` of the latest change to what the concept describes. Only if amended. |
| `tags` | List of one or more of the [ADR tags](../style.md#header-fields-and-status). Always present. |
| `related` | List of the ADRs and concepts a reader should know, e.g. `[ADR-0009, AC-0006]`. Only if any. |

| Status | Meaning |
|---|---|
| `draft` | Being written or reviewed; may not match the system yet. |
| `current` | Describes the system as it is, or as it is meant to be built. |
| `outdated` | No longer matches the system; kept until it is rewritten or removed. |

`scripts/docs_check.py` checks the names, titles, fields and every `AC-NNNN` reference in the tree, and generates the index below from the frontmatter ([ADR-0048](../adrs/adr-0048-architecture-concepts.md)); do not edit it by hand.
It runs as a pre-commit hook and as `just docs-check`.

## Index

<!-- ac-index:start -->
| # | Title | Status | Tags |
|---|---|---|---|
| [0000](ac-0000-monorepo-overview.md) | Monorepo architecture overview | current | build, release, deploy, testing |
| [0001](ac-0001-file-transfer-and-storage.md) | File transfer and storage | current | backend, data, security |
| [0002](ac-0002-metadata-lifecycle.md) | Metadata lifecycle | current | backend, data |
| [0003](ac-0003-authentication-and-authorization.md) | Authentication and authorization | current | security, backend, frontend |
| [0004](ac-0004-parallelization-in-upload-and-download.md) | Parallelization in upload and download | current | backend |
| [0005](ac-0005-testing-strategy.md) | Testing strategy | current | testing, backend |
| [0006](ac-0006-asynchronous-interservice-communications.md) | Asynchronous interservice communications | current | backend, events |
| [0007](ac-0007-file-upload.md) | File upload | outdated | backend, data, events |
| [0008](ac-0008-metadata-and-file-journeys.md) | Metadata and file journeys | current | backend, data, events |
| [0009](ac-0009-kafka-cascade-map.md) | Kafka cascades map | current | events |
| [0010](ac-0010-db-migrations.md) | MongoDB migrations in services | current | backend, data, deploy |
<!-- ac-index:end -->
