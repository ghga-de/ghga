# Exploration and conception for the metadata service refactoring (crayfish)
**Epic Type:** Exploratory Epic

**Attention: Please do not put any confidential content here.**

## Principle Components of Exploration:

- ~~Strategy for auto generation of the spreadsheet template from the schema~~
- ~~Strategy for achieving adaptability of the schema to different use cases~~
- ~~Concept for independence of services and schema~~
- strategy for automatic rollout of schema updates
- strategy for handling existing metadata in case of a schema update
- strategy for sharing metadata across submissions (if necessary)
- strategy for enriching the schema with validators/linters for logic that cannot be described using the declarative schema
- strategy for data deletions when using event sourcing
- tools and patterns to be evaluated:
    - ~~LinkML documentation driven design using runtime interpretation~~
    - GraphQL as alternative for modeling APIs
    - ElasticSearch or Solr as Alternative to Mongodb-based search
    - CQRS and storage of metadata in an event history
    - separation of write and read representations of metadata

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
