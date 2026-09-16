# Metadata refactoring proof of concept (Pacific Lamprey)
**Epic Type:** Implementation Epic

**Attention: Please do not put any confidential content here.**

## Scope:
The aim of this study is to create a proof of concept implementation of the strategy
outlined in
https://docs.ghga-dev.de/main/architecture_concepts/ac002_metadata_lifecycle.html.


## Additional Implementation Details:

- An implementation that can be run by data stewards locally,
  no production-ready and independently deployed services.
- includes:
    - basic in implementation of the submission store
    - Validation of metadata upon submission against the linkML schema
    - Essential transformations and generation of associated artifacts, including:
        - Fully embedded datasets
        - Custom embeddings
        - Non-restricted (public) metadata
        - Summary statistics
        - Mongodb-based search index
    - Loading the above artifacts into deployed mongodb instances
    - REST APIs for querying the above artifacts
- does not include:
    - difference between published and non published submissions
    - reviews of submissions
    - status changes for submissions (all submissions will be immediately be treated
      as completed and published)
    - Deprecation and emptying of submissions
    - multiple schemas and schema migrations

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
