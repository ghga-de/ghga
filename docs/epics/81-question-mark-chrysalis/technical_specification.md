# Preliminary Experimental Metadata (EM) Transformation Service (Question Mark Chrysalis)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

The goal of this epic is to implement a service for the transformation of Experimental Metadata (EM) from one representation/model to another. 
This service shall provide functionality around the configurable workflow concept from the `metldata` library to enable these transformations.
To this goal, it needs to keep track of the transformation workflows, original and derived data/schema and workflow routes in its database.


### Terminology

`Experimental Metadata (EM)`: Data describing the experimental process of generating the Research Data archived in GHGA.

`Experimental Metadata Ingress Models (EMIM)`: Schemas that define the structure and format of experimental metadata as it enters the GHGA system from external sources. It follows SchemaPack format. Currently, GHGA supports only a single data ingress model for experimental metadata, which is the [ghga-metadata-schema](https://github.com/ghga-de/ghga-metadata-schema), but this epic is part of the effort to lift that restriction.

`Universal Discovery Model`: A common target representation to which all the EMs are transformed, serving as a basis for data queries and data display via the GHGA Data Portal. 

`EMPack`: Experimental metadata in datapack format. It follows a relational data schema corresponding to one of the EMIMs.

`AnnotatedEMPack`: A datapack enriched with additional information such as accessions that help integrate the EMPack into the archive.

`Workflow`: Instructions on how to produce a certain datapack/schemapack representation from another datapack/schemapack. The workflows are defined by the `metldata` library on which the transformation service will be built.

`Route`: Information on which specific workflow is used to produce datapack compliant with the output model when presented with datapack compliant with the input model.

`Model`: an object that holds all information necessary for the transformation service regarding an EMIM or transformed model.

### Included/Required:

- Implement a service that persists the `AnnotatedEMPack`, `Model`, `Workflow`, and `Route` entities.
- Implement logic to process incoming AnnotatedEMPacks, execute the corresponding workflows and store the resulting AnnotatedEMPacks if required.
- Implement code to manage changes in models, workflows and routes, e.g. by creating universal schema descriptions from the ingress schema descriptions and re-transforming the AnnotatedEMPacks.


### Core entities

#### `Model`

- purpose: describes how models are represented in the service.

data structure:
```python
from pydantic import BaseModel

class RawModel(BaseModel):
   name: str
   description: str | None
   is_ingress: bool
   version: str | None
   schema: SchemaPack | None
   publish: bool 

class Model(RawModel):
   schema: SchemaPack
   order: int

```
- RawModel.name: Unique identifier / human-readable name of the model.
- RawModel.description: Human-readable description.
- RawModel.is_ingress: Boolean, true for EMIMs.
- RawModel.version: Schema version, None if it is not an EMIM
- RawModel.schema: Schema in SchemaPack format, None if it is not an EMIM and not yet computed
- RawModel.publish: Boolean indicating whether the AnnotatedEMPacks conforming to the schema should be published
- Model.order: Order in a topological ordering of the schemas in the transformation graph
- Model.schema: Schema in SchemaPack format, always defined after derivation.

`RawModel` is used when deserializing the configuration from YAML files, as it does not include the `order` field that is derived after configuration validation. `RawModel` must include a validator to ensure that EMIMs (is_ingress = true) always have a `schema` defined. And the `schema` is None for non-EMIMs when deserializing the configuration.

`Model` is used for the DAO. Since the models are stored in the database only after the config is validated, the `Model` class dictates that `order` and `schema` are not null. 

#### `Workflow`

- Purpose: holds a metldata-compatible workflow definition used to transform schema/data.

data structure:
```python
class Workflow(BaseModel):
   name: str
   description: str | None
   workflow: metldata.workflow.base.Workflow
```

- name: Unique identifier / human-readable name for the workflow. Indicates the purpose of the workflow for easier debugging and understanding of the operations.
- description: Optional longer description of the workflow.
- workflow: Workflow definition in metldata format.


#### `Route`

- Purpose: describe the routes for transforming models and their corresponding data by referencing the workflow, the input and output models involved in each transformation by name.

data structure:

```python
class Route(BaseModel):
   name: str
   input_model_name: str
   output_model_name: str
   workflow_name: str
```

- name: Unique identifier / human-readable name for the workflow route. Follows the format of `{input_model_name}:{workflow_name}:{output_model_name}`.
  
  The model must include a validator to ensure name consistency. Only one representation of the name should be provided in the transformation configuration. The validator automatically derives any missing parts: if only the composite name is given, it extracts the individual names; if only the individual names are provided, it constructs the composite name.

- input_model_name: Name of the input model accepted by the route.
- output_model_name: Name of the output model produced by the route.
- workflow_name: Name of the workflow to apply on the route.


#### `RawConfig`

- Purpose: describe the current active transformation configuration

data structure:

```python

class RawConfig(BaseModel):
   models: list[RawModel]
   workflows: list[Workflow]
   routes: list[Route]

```

- RawConfig.models: List of RawModel objects defining the transformation graph.
- RawConfig.workflows: List of Workflow objects available.
- RawConfig.routes: List of Route objects composing the graph.

#### `AnnotatedEMPack`

Purpose: holds incoming and derived annotated EM datapacks that are to be processed or published.

data structure:

```python
class AnnotatedEMPack(BaseModel):
   id: uuid
   model_name: str
   original_id: str | None
   data: DataPack
   annotation: dict
```
- id: Unique identifier for the AnnotatedEMPack.
- model_name: Unique name of the model the EMPack conforms to
- original_id: ID of the original incoming EMPack it was derived from. None if it is an original EMPack
- data: EMPack conforming to the model identified by `model_name`
- annotation: Object with information from other models held by the service 


#### Database Layer

The em-transformation-service interacts with a database containing the core entities described above.

On startup, the service reads all Models, Workflows and Routes from a config YAML and from the database. These objects should be kept completely in memory and they are only written back to the database if they are in a consistent, validated state with all necessary information (derived schemas, ordering) already computed.

If the content of the config YAML file corresponds to what is stored in the database, the service continues to use the known-valid and pre-computed config from the database. If there are any changes in the YAML config, it will be validated, and the missing information (derived schemas, ordering) re-computed. If there are any errors, the YAML config will be rejected, otherwise stored in the database as new configuration.

AnnotatedEMPacks are populated from incoming events (from the GHGA Study Repository) and transformation outputs. Only published data is stored persistently (using an outbox DAO). Intermediate transformed data is kept in memory as long as they are needed for running a full transformation graph corresponding to a single original piece of data, as explained in a later section..

#### Transformation Configuration

The transformations are configured through the models, workflows and routes.

Routes define how to transform an input model into an output model by specifying the workflow to apply and the expected output model.

Routes also define a graph where models are nodes and routes are directed edges. The source nodes of this graph are the EMIMs. The graph must not contain any "diamonds", i.e. there must be at most one directed path between any two models in the graph. This also implies that the graph does not contain any cycles, i.e. is a directed acyclic graph (DAG). 

We enforce this stronger unique-path property because "diamond" shapes indicate unnecessary redundancy that should be avoided, and because it eliminates any ambiguity in how data are transformed.

This graph structure is used to validate the transformation configuration and to determine the processing order of schemas during model derivation and configuration changes.

#### User Journeys: Transformation Configuration Validation & Model Derivation

When manually triggered—or when the configuration changes—the service derives the output schemas for all routes.

1. Validate the transformation configuration:

   1. Verify that all workflows and EMIMs (i.e., models with is_ingest = true) referenced by the routes exist in the configuration.
   2. Ensure that EMIMs do not appear as the output models of any routes.
   3. Validate schemas using the SchemaPack library and workflows using the metldata library.
   4. Confirm that the graph meets the unique-path requirement and is therefore acyclic.
   5. Compute a topological order of the graph’s nodes—e.g. using Kahn’s algorithm—so that each model is processed only after all its dependencies when visiting the models in that order.
   6. Update the order field of each model based on the computed topological order.
   7. If the validation fails:
      1. Reject the configuration.
      2. Re-load the previous valid configuration from the database.
      3. If there is no configuration stored in the database yet, stop the service

2. Traverse the transformation graph starting from the EMIMs, following the topological order. For each route:
   1. Use metldata to run the workflow identified by `workflow_name` on the input model’s schema referenced by `input_model_name` and compute the derived schema.
   2. Update the output model’s schema accordingly.
   3. If any errors or conflicts occur, abort the operation and report them.


The validation (including the model derivation) should be protected by a global lock that would prevent other instances of the service from running the validation and model derivation in parallel, and would also stop the processing of AnnotatedEMPack transformations while the lock is active.

This lock could be implemented via a special "lock" collection in the database that would contain a certain document while the lock is active.


#### User Journeys: Service Consumer Transforms An Original AnnotatedEMPack

The transformation operation is triggered when the service receives either an “original AnnotatedEMPack upsert” event or a “re-transform AnnotatedEMPack” event.

1. Build the dirty map: Query the AnnotatedEMPacks collection for all data where `original_id` matches the incoming original data's ID. Extract each data's ID and model name, then create a mapping from model names to data IDs. This "dirty map" tracks data that need to be either re-created or deleted.

2. Initialize the transformed map: Create a mapping from model names to data. This map will accumulate all data generated during this transformation operation. Initialize it with a single entry: the original model name mapped to the incoming original data.

3. Traverse the transformation graph: Starting from the EMIM and following the topological order, perform the following for each model:
   1. Get the route that has the current model as its input. Due to the unique-path property, exactly one route must exist; raise an error otherwise.
   2. Retrieve the data from the transformed map using the route’s input model. This is the “input data” for this step. It should always exist at this point if the topological order was computed correctly, and we can raise an error at this point if this is not the case.
   3. Compute the transformed data using the input data and the route's workflow.
   4. If the current model exists in the dirty map, remove it from there and update the transformed map with the newly transformed data.
   5. Otherwise, add the transformed data to the “transformed map” with a newly generated id, setting its `model_name` to the current model name, and its original_id field to the original data id.

4. Apply database updates: Upsert all transformed data that should be published, and delete any remaining data listed in the dirty map.

This approach avoids deleting "dirty" data during recreation, preventing resources from temporarily disappearing mid-transformation. It also keeps intermediate data in memory, reducing unnecessary database operations.

#### User Journeys: Configuration Change

This operation is triggered when a change to the configuration YAML file is detected when the service is started.

The service detects configuration changes by comparing the configuration in the database with the configuration stored in the config YAML.

When comparing the configuration, the objects should be compared recursively for equality. This is done automatically in Python when the config is deserialized as a dict or Pydantic object. However, care must be taken to not compare fields that do not exist in the raw configuration (order and derived schemas). We could implement a custom equality method to properly compare Models with RawModels in that regard.

When they differ, the service adopts the new configuration and performs:

1. Re-derivation of all transformed schemas (as described in "Model Derivation")
2. Re-transformation of all original AnnotatedEMPacks (as described in "Service Consumer Transforms An Original AnnotatedEMPack")


### Not included (but possible future extensions):

- A REST API to retrieve the currently used public schemas, which would be useful for frontend developers for inspection purposes.
- A REST API to push configuration data instead of loading it from YAML files at startup.
- Configuration versioning to maintain a full history of changes and enable rollbacks to previous versions.
