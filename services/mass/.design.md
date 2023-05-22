<!-- Please provide an overview of the architecture and design of the code base.
Mention anything that deviates from the standard triple hexagonal architecture and
the corresponding structure. -->

This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.

This service is currently designed to work with MongoDB and uses an aggregation pipeline to produce search results.

Typical sequence of events is as follows:
1. Requests are received by the API, then directed to the QueryHandler in the core.

2. From there, the configuration is consulted to retrieve any facetable properties for the searched resource class.

3. The search parameters and facet fields are passed to the Aggregator, which builds and runs the aggregation pipeline on the appropriate collection. The aggregation pipeline is a series of stages run in sequence:
   - The first stage runs a text match using the query string.
   - The second stage applies a sort based on the IDs.
   - The third stage applies any filters supplied in the search parameters.
   - The fourth stage extract facets.
   - The fifth/final stage transforms the results structure into {facets, hits, hit count}.
4. Once retrieved in the Aggregator, the results are passed back to the QueryHandler where they are shoved into a QueryResults pydantic model for validation before finally being sent back to the API.
