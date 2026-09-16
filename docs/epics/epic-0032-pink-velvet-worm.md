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
    - class_name: string - the name of the document type being searched (e.g. "DatasetEmbedded")
    - skip: integer (default 0) - the number of initial results to skip. Used for pagination.
    - limit: integer (default 10) - the number of results to return, representing one page's worth of results.
    - query: string - the search string
    - filters: list (optional) - contains dictionaries with keys "key" and "value" for specifying filters
  - Response Body:
    - facets: list - contains the facets (if faceting)
    - count: integer - hit count (although 'hits' will only contain up to 'limit' elements)
    - hits: list - contains the search results

- GET /rpc/search-options: Get a list of searchable classes (resource types) and their facetable properties.
  - Response Body:
    - searchable_classes: JSON - for each class, contains the name of the class, a description, and its facetable properties

## Additional Implementation Details:

### Configuration

The searchable classes, or resource types, will be moved into configuration and made available at deploy time. Therefore, any class intended to be made available through the search service will need to be defined under the **searchable_classes** config variable. Each searchable class should contain the **description** as a string and any **facetable_properties** as a list of objects with two fields each: "key", which contains the raw property name, and "name", which contains the user-friendly name.

Example:

```yaml
searchable_classes:
  Dataset:
    description: Dataset grouping files under controlled access.
    facetable_properties:
    - key: type # a property directly part of the dataset
      name: Type
    - key: study.type # a property that is part of study that is embedded into this dataset
      name: Study Type
    - key: study.project.alias # a property part of a deeply embedded resource
      name: Project Alias
  Study:
    description: A study addressing a specific research question.
    facetable_properties:
    - key: study.type
      name: Study Type
    - key: study.project.alias
      name: Project Alias
```

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
