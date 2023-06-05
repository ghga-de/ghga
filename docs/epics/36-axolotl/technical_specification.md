# Biomedical Metadata Mocking (Axolotl)
**Epic Type:** Implementation Epic

## Scope
### Outline:
This epic implements mocks for all Metadata Repository Service and Metadata Search Service API calls consumed by the Data Portal UI.

### Included/Required:
The epic includes and requires:
- the addition of data objects to be mocked based on the current metadata model and currently used metadata objects in the deployed version
- that there is at least one data object for each edge case (e.g. at least one object with/without an EGA Accession ID (vs. a GHGA Accession ID), a DAC form, a linked study), e.g. by modifying one template object

### Not included:
This epic does not include:
- the addition of 'realistic' data; the data will be used to test what is necessary to test the display of all features available on the data portal, thus additional fields that are not used will not be included.

## User Journeys (optional)

This epic covers the following user journeys:

Browsing data:
- The user views the summary of the entire dataset of metadata objects
- The user views the summary of a single metadata object
- The user views the details of a single metadata object, including list of files, experiments, and samples
- The user requests access to the data of a specific metadata object through the "Request" access button in either the browse page or the single dataset view page
- The user filters datasets by keyword
- The user filters datasets by filter facets

Please note, filtering and specifying keywords will not change the displayed items since the response from the metadata repository service is mocked and static. This should also be documented in the readme.

## API Definitions:

### Metadata Search Service

Searching through our dataset of metadata objects:

- `POST /rpc/search/?document_type={documentType}&return_facets=true&skip={skip}&limit={limit}`
- `documentType`: the type of metadata objects we wish to search for [(see docs)](https://ghga-de.github.io/ghga-metadata-schema/docs/type/), only need to support "Dataset"
- `skip`: the offset from 0 from which we wish to start our search (and retrieve results). Used for pagination.
- `limit`: the amount of search results we wish to be returned.
- request body:
  - `query`: a keyword to filter the results by; to not filter by keyword, `query` should be set to `"*"`
  - `filters`: an array of `{key : string, value : string}` JSON objects, for which `key` is the facet code (e.g. `experiment_type`) and `value` is the value by which to filter.

The response body is a `searchResponseModel` object (`{count: number, hits: hitModel[], facets: facetModel[]}[]`).

### Metadata Repository Service

Requesting the details of a dataset:

- `GET /datasets/{datasetId}?embedded={embedded}`
- `datasetId`: the internal (UUID) of the dataset in question
- `embedded`: if true, the API call returns the dataset object with all children (e.g. files, studies, experiments) fully embedded within the dataset object (i.e. the file name, type, size, etc. vs. the UUID of the file object).
- no request body

The reponse body is either a `datasetModel` or a `datasetEmbeddedModel`.

Requesting the summary of a dataset:

- `GET /dataset_summary/{datasetId}`
- `datasetId`: the internal (UUID) of the dataset in question
- no request body

The reponse body is a `datasetDetailsSummaryModel`. 

Requesting the summary of the entire dataset of metadata objects:

- `GET /metadata_summary/`
- no request body

The reponse body is a `metadataSummaryModel`. 

## Additional Implementation Details:

[The GHGA Metadata Model schema is large, and better documented in its own page](https://ghga-de.github.io/ghga-metadata-schema/docs/).

All API calls for the Metadata Search and Repository services are already implemented, and the mocks should theoretically be easily integrated once the mock data is created.

## Human Resource/Time Estimation:

Number of sprints required: 2 or 3.

Number of developers required: 1.
