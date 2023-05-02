# Reimplementation of metadata search service (Pink Velvet Worm)
**Epic Type:** Implementation Epic


## Scope
### Outline:
The metadata search service will be rewritten to conform to standards/best practices of our current architectural approach. The focus is on re-implementing the service and not on adding or altering functionality.

### Included/Required:
- Restructuring the project to conform to the Triple Hexagonal architectural approach
- Implementing usage of tools like hexkit where applicable
- Testing

### Not included:
- Implementing additional features like displaying search hit context will not be included.

## API Definitions:

The API will remain essentially the same, but all parameters will be moved into the request body (no query string parameters).
The hits returned in the response will contain the fully embedded documents, which differs from the current search service in that the current service returns only the datasets' information, and all embedded references are expanded upon in subsequent queries.

### RPC:

- POST /rpc/search: Submit search query
  - Request Body:
    - document_type: string - the name of the document type being searched (e.g. "Dataset")
    - return_facets: boolean (default False)- Whether or not to facet results
    - skip: integer (default 0) - the number of initial results to skip. Used for pagination.
    - limit: integer (default 10) - the number of results to return, representing one page's worth of results.
    - query: string - the search string
    - filters: list (optional) - contains dictionaries with keys "key" and "value" for specifying filters
  - Response Body:
    - facets: list - contains the facets (if faceting)
    - count: integer - hit count (although 'hits' will only contain up to 'limit' elements)
    - hits: list - contains the search results


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
