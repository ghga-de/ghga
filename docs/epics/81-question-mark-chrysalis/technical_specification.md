# Preliminary Experimental Metadata (EM) Transformation Service (Question Mark Chrysalis)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

The goal of this epic is to implement a service for the transformation of Experimental Metadata (EM) from one representation/model to another. 
This service shall provide functionality around the configurable workflow concept from the `metldata` library to enable these transformations.
To this goal, it needs to keep track of the transformation workflows, original and derived data and workflow routes in its database.


![em-transformation-service overview](./images/em_transformation_service.png)


### Terminology

`Experimental Metadata (EM)`: Data describing the experimental process of generating the Research Data archived in GHGA.

`Experimental Metadata Ingress Models (EMIM)`: Schemas that define the structure and format of experimental metadata as it enters the GHGA system from external sources. Currently, GHGA supports only a single data ingress model for experimental metadata, which is the [ghga-metadata-schema](https://github.com/ghga-de/ghga-metadata-schema), but this epic is part of the effort to lift that restriction.

`Universal Discovery Model`: A common target representation to which all the EMs are transformed, serving as a basis for data queries and data display via the GHGA Data Portal.  

`EMPack`: Experimental metadata in datapack format. It follows a relational data schema corresponding to one of the EMIMs.

`AnnotatedEMPack`: A datapack enriched with additional information such as accessions that help integrate the EMPack into the archive.

`annotatedEMPacks`: A MongoDB collection of AnnotatedEMPack objects.

`Workflow`: Instructions on how to produce a certain data/model representation from another data/model. The workflows are defined by the `metldata` library on which the transformation service will be built.

`workflows`: A MongoDB collection of Workflow objects.

`WorkflowRoute`: Information on which specific workflow is used to produce data compliant with the output model when presented with data compliant with the input model.

`WorkflowRoutes`: A MongoDB collection of WorkflowRoute objects.


### Included/Required:

- Implement logic to process incoming AnnotatedEMPacks, execute the corresponding workflows and store the resulting AnnotatedEMPacks if required.
- Implement service start-up logic to derive missing schemas for workflow routes with empty output schemas.
- Implement MongoDB collections to store AnnotatedEMPacks, Workflows and WorkflowRoutes.

#### Collections


`Schemas`

- purpose: store schemas

data structure:
```python
class Schema(BaseModel):
   id: uuid
   name: str
   original: bool
   version: str | None
   content: SchemaPack | None
   publish: bool 
   order: int | None

```

`Workflows`

- Purpose: store metldata-compatible workflow definitions used to transform schemas/data.

data structure:
```python
class TransformationWorkflow(BaseModel):
   id: uuid
   name: str | None
   description: str | None
   workflow: metldata.workflow.base.Workflow
```


`WorkflowRoutes`

- Purpose: describe named routes that bind workflows, input schema types and produced output schema types, and whether outputs should be published.

data structure:
```python
class WorkflowRoute(BaseModel):
   id: uuid
   name: str | None
   input_schema_id: uuid
   output_schema_id: uuid
   workflow_id: uuid
```


`AnnotatedEMPacks`

Purpose: store incoming and derived annotated EM datapacks that are to be processed or published.

data structure:
```python
class AnnotatedEMPack(BaseModel):
   id: uuid
   schema_id: uuid
   original_id: uuid | None
   datapack: DataPack
   annotation: dict
```

#### Implementation Details of Collections

The implementation of the EM transformation service will involve the following key components.

1. `Schemas`
   
   Consists of Schema objects
   * `id` is a unique identifier of the schema
   * `name` is a human readable name of the schema
   * `original` is a boolean flag indicating whether the schema is an original or derived schema
   * `version` is the version of the schema (aka type of the schema), initially None if it is not an original schema
   * `content` is the schema in schemapack format, initially None if it is not an original schema
   * `publish` is a boolean flag indicating whether the derived datapacks conforming to this schema should be published
   * `order` is the order in a topological ordering of the schemas in the transformation graph, initially None if it is not an original schema
   

   This collection is populated manually with the defined ghga schemas.

   These are original schemas (`original: true`) stored in the `Schemas` and serve as the entry point for data that will be transformed into Universal GHGA Models. EMIM schemas provide a stable interface for data providers and may be more flexible or permissive than internal canonical models to accommodate varied input sources.

2. `Workflows`

   Consists of TransformationWorkflow objects
   * `id` is a unique identifier for a workflow
   * `name` is a human readable name for the workflow
   * `description` is a more verbose description of the workflow
   * `workflow` is the definition of the workflow in metldata format

   This collection is populated manually with the defined ghga transformation workflows.


1. `WorkflowRoutes`

   Consists of WorkflowRoute object
   * `id` is a unique identifier for the workflow route
   * `name` is a human readable name for the workflow route
   * `input_schema_id` is the id of the input schema that the workflow route accepts
   * `output_schema_id` is the id of the output schema that the workflow route produces 
   * `workflow_id` is a workflow identifier that is to be applied on a data / schema  
   

   This collection is populated manually with the defined ghga workflow routes.  
   An empty workflow_output_schema indicates the route requires schema derivation at startup.  

1. `AnnotatedEMPacks`

   Consists of AnnotatedEMPack objects.
   * `id` is a unique identifier for the AnnotatedEMPack
   * `schema_id` is the identifier of the schema the EM datapack conforms to
   * `original_id` is the identifier of the original AnnotatedEMPack from which this AnnotatedEMPack was derived; it is None if this is an original AnnotatedEMPack
   * `datapack` is the EM in datapack format that conforms to the schema identified by `schema_id`
   * `annotation` is an annotation object with information from other models held by the service

   This collection is filled from two sources: incoming events GHGA Study Repository and outputs of executed workflow routes.

   Note that we only store published datapacks on the collection. If there are intermediate transformed datapacks, they will only be created and kept in memory as long as they are needed for running a full transformation graph corresponding to a single original datapack.

#### Transformation Configuration

A transformation is configured through the Schemas, Workflows and WorkflowRoutes collections.

Workflow routes defines the transformation paths from input schemas to output schemas using specific workflows. Each workflow route specifies which workflow to apply for a given input schema and what output schema to produce. 

Workflow routes also define a a graph structure where schemas are nodes and workflow routes are directed edges. The source nodes of this graph are the “original schemas” aka EM models defined as schemapacks. The graph must not contain any cycles, i.e. it should be a directed acyclic graph (DAG). Additionally, the graph must not contain any "diamonds", i.e. there must be at most one directed path between any two schemas in the graph.

This graph structure is used to validate the transformation configuration and to determine the order in which schemas need to be processed during service startup and when processing incoming AnnotatedEMPacks.

#### Transformation Configuration Validation

Transformation configuration validation includes:

1. Check the graph follows a tree-like structure, i.e. it conforms to the unique path requirement mentioned above.
2. Calculate the topological order of the nodes in the graph using an algorithm similar to Kahn's algorithm, so that the schemas are ordered in a way that if we process the schemas in that order, the previous schemas have already been processed.
3. Update the `order` field of each schema in the `Schemas` according to the calculated topological order. 
4. Check the workflows and the original schemas referred by the workflow routes exist in their corresponding collections.

#### User Journeys: Schema Derivation (Manual Trigger)

When manually triggered, the service derives the output schemas for all workflow routes with empty output schemas. 

1. Validate the transformation configuration of the workflow routes.
2. Traverse the schemas in the transformation graph starting with the original schema, in topological order. For every route execute the following:
   1. Retrieve the workflow of the corresponding `workflow_id` from the `Workflows`
   2. Retrieve the schema corresponding to the `input_schema_id` from the `WorkflowRoutes`.
   3. Call metldata to execute the workflow on the input schema to compute the derived schema.
   4. Record the derived schema in the `Schemas` and save its id to the `output_schema_id` of the WorkflowRoute.
3. If there are any errors / conflicts, the operation shall fail and report the error.


#### User Journeys: Service Consumer Receives An Original AnnotatedEMPack

The transformation operation is triggered when the service consumer receives "original annotated Em Pack" or a “re-transform metadata” event.

1. Fetch the datapack ids and corresponding schema ids of all datapacks in the collection where the original_id field matches our original datapack id. Create a mapping of these schema ids to their datapack ids that we call “dirty map”, because all of these datapacks need to be either re-created or deleted.
2. Create a “transformed map” that maps schema ids to datapacks. This will hold the datapacks that have been transformed in this operation already. Initialize it with just the original schemapack id mapping to the original datapack.
3. Traverse the schemas in the transformation graph starting with the original schema, in topological order. For all of these schemas, do the following:
   1. Get a route that has the current schema as input. Since we do not allow multiple routes between the same two schemas, there should be at most one such route. Raise an error if there are multiple such routes.
   2. Get the datapack from the “transformed map” that corresponds to the input schema of that route. This is the “input datapack” for this step. It should always exist at this point if the topological order was computed correctly, and we can raise an error at this point if this is not the case.
   3. Compute the transformed datapack using the input datapack and the workflow route.
   4. If the current schema id is in the “dirty map”, remove it there and update the “computed map” with the transformed datapack.
   4. Otherwise, add the transformed datapack to the “computed map” with a newly generated id, setting its schema_id to the current schema id, and its original_id field to the original datapack id.
4. Finally, upsert all entries in the “transformed map” to the database that should be published, and delete all remaining entries in the “dirty map” from the database.

This course of action avoids deleting “dirty” datapacks while they are recreated, since that would make the corresponding resources disappear while the transformation is ongoing. It also keeps any intermediate datapacks in memory, avoiding unnecessary database operations and operations.

#### User Journeys: Configuration Change

The “configuration change” operation should be triggered whenever anything in the Schemas, Workflows or WorkflowRoutes collection changes. It will be good to collect such changes and make them all at once, before triggering this operation, because it is very costly.

The configuration change will trigger the following operations:
1. Validate the transformation configuration
2. Recalculate the topological order of the schemas and update the `order` field
3. Re-compute the schemapacks of all transformed schemas
4. Re-run the transformations for all original datapacks

### Not included:

- The service has no REST API to configure workflows but instead reads workflows from the database, where workflows must be stored in a predefined schema or format as required by the service.

- The service has no event consumer to populate its collection of known models but instead reads the models from a database where they have to be stored manually
