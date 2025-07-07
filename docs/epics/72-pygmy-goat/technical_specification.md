# Hexkit Documentation (Pygmy Goat)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
`Hexkit` currently has very little documentation regarding its use, terminology,
or architectural concepts. Some of this knowledge *is* documented in an unconsolidated
fashion, with files spread across Confluence, Google Docs, and the internal docs
site. However, developers or even hypothetical third parties working with or
contributing to `hexkit` do not currently have access to the comprehensive and
consolidated documentation that the library warrants. This epic will remedy that.
The aggregated documentation will be written in Markdown and processed using MkDocs.
Optionally, we can publish it using GitHub Pages. This approach ensures accessibility
for both internal developers and third parties.


### Included/Required:
The following points should be covered in the documentation:
- Glossary
- Update, improve and expand the existing code in the examples directory
  - Document these examples, and add some more usage examples if needed
- Architectural Concepts (Triple Hexagonal Architecture, DLQ, Outbox, DAOs, etc.)
- Testing Tools (persistent vs clean fixtures, session-scoped containers, etc.)
- Requirements for adding new functionality, e.g. new protocols or new DAO providers
- Auto-generated API reference docs


### Additional Implementation Details
The following is one example of a possible structure for the documentation:

- Architecture Concepts
  - Triple Hexagonal Architecture
  - Event-Driven Architecture
- Protocols
  - Existing protocols
  - Adding protocols
- Providers
  - S3
    - Overview
    - Test utilities
      - Container fixture and fixture reset/cleanup function
      - Accompanying fixtures/utilities
  - Kafka
    - Overview
    - Outbox Pattern
    - Persistent Publisher
    - When to use outbox vs persistent publisher
    - DLQ
    - Test utilities
      - Container fixture and fixture reset/cleanup function
  - MongoDB
    - Overview
    - Role in outbox pattern
    - Role in persistent publisher
    - Migration Tools
    - Test utilities
      - Container fixture and fixture reset/cleanup function
- Adding providers
- Glossary
- Usage Examples should include the following, if they don't already:
  - Basic Kafka Pub/Sub
  - Basic DAO
  - Basic S3
  - Dependency Injection (as in most of our `inject.py` modules)
  - Logging
  - Correlation IDs
  - Migration Tools
- Logging
- Correlation IDs


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 2
