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

`Experimental Metadata Ingress Models (EMIM)`: Schemas that define the structure and format of experimental metadata as it enters the GHGA system from external sources. Currently, GHGA has a single data ingress model for experimental metadata, which is the ghga-metadata-schema. 

`Universal Discovery Model`: A common target representation to which all the EMs are transformed into, used for data queries and data display via th GHGA Data Portal.  

`EMPack`: Experimental metadata in datapack format. It follows a relation data schema and compatible with one of the EMIMs.

`AnnotatedEMPack`: A datapack enriched with additional information. 

`AnnotatedEMPackCollection`: A MongoDB collection of AnnotatedEMPack objects.

`Workflow`: Instructions on how to produce a certain data/model representation from another data/model. The workflows are defined by the `metldata` library on which the transformation service will be built.

`WorkflowCollection`: A MongoDB collection of Workflow objects.

`WorkflowRoute`: Information on which specific workflow is used to produce data compliant with the output model when presented with data compliant with the input model.

`WorkflowRoutesCollection`: A MongoDB collection of WorkflowRoute objects.


### Included/Required:

- Implement logic to process incoming AnnotatedEMPacks, execute the corresponding workflows and store the resulting AnnotatedEMPacks if required.
- Implement service start-up logic to derive missing schemas for workflow routes with empty output schemas.
- Implement MongoDB collections to store AnnotatedEMPacks, Workflows and WorkflowRoutes.

#### Collections


`SchemaCollection`

- purpose: describe schemas


```python
class Schema(BaseModel):
   id: uuid
   name: str
   original: bool
   version: str | None
   content: SchemaPack | None
   

```

`WorkflowCollection`

- Purpose: store metldata-compatible workflow definitions used to transform schemas/data.

data structure:
```python
class TransformationWorkflow(BaseModel):
   id: uuid
   name: str | None
   description: str | None
   workflow: metldata.workflow.base.Workflow
```


`WorkflowRoutesCollection`

- Purpose: describe named routes that bind workflows, input schema types and produced output schema types, and whether outputs should be published.


```python
class WorkflowRoute(BaseModel):
   id: uuid
   name: str | None
   input_schema_id: uuid
   output_schema_id: uuid
   workflow_id: uuid
   publish: bool 
   order: int | None # Since it will be calculated at startup, it will initially be None.

```
**REMARK1: i think publish should be a part of workflow route, the model collection should not keep information about what happened to the transformed data. it is not the responsibility of the model collection to know whether the data is published or not.**


**REMARK2: I moved the order from the schema collection to the workflow route collection, since the order is more related to the workflow routes than the schemas themselves.**


`AnnotatedEMPackCollection`

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

1. `SchemaCollection`
   
   Consists of Schema objects
   * `id` is a unique identifier of the schema
   * `name` is a human readable name of the schema
   * `original` is a boolean flag indicating whether the schema is an original or derived schema
   * `version` is the version of the schema (aka type of the schema), initially None if it is not an original schema
   * `content` is the schema in schemapack format, initially None if it is not an original schema
   

   This collection is populated manually with the defined ghga schemas.

   These are original schemas (`original: true`) stored in the `SchemaCollection` and serve as the entry point for data that will be transformed into Universal GHGA Models. EMIM schemas provide a stable interface for data providers and may be more flexible or permissive than internal canonical models to accommodate varied input sources.

1. `WorkflowCollection`

   Consists of TransformationWorkflow objects
   * `id` is a unique identifier for a workflow
   * `name` is a human readable name for the workflow
   * `description` is a more verbose description of the workflow
   * `workflow` is the definition of the workflow in metldata format

   This collection is populated manually with the defined ghga transformation workflows.


1. `WorkflowRoutesCollection`

   Consists of WorkflowRoute object
   * `id` is a unique identifier for the workflow route
   * `name` is a human readable name for the workflow route
   * `input_schema_id` is the id of the input schema that the workflow route accepts
   * `output_schema_id` is the id of the output schema that the workflow route produces 
   * `workflow_id` is a workflow identifier that is to be applied on a data / schema  
   * `publish` is a boolean flag indicating whether the output of the workflow route shall be published in form of an AnnotatedEMPack to AnnotatedEMPack collection.
   * `order` is the order in a topological ordering of all workflow routes

   This collection is populated manually with the defined ghga workflow routes.  
   An empty workflow_output_schema indicates the route requires schema derivation at startup.  

1. `AnnotatedEMPackCollection`

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

Workflow routes defines the transformation paths from input schemas to output schemas using specific workflows. Each workflow route specifies which workflow to apply for a given input schema and what output schema to produce. The `publish` flag indicates whether the resulting AnnotatedEMPack should be stored in the AnnotatedEMPackCollection.

Workflow routes also define a a graph structure where schemas are nodes and workflow routes are directed edges. The source nodes of this graph are the “original schemas” aka EM models defined as schemapacks.

This graph structure is used to validate the transformation configuration and to determine the order in which schemas need to be processed during service startup and when processing incoming AnnotatedEMPacks.

#### Transformation Configuration Validation

Transformation configuration validation includes:

1. Check the workflow routes graph do not contain cycles, i.e. it is a directed acyclic graph
2. Calculate the topological order of the nodes in the graph using Kahn's algorithm, so that the schemas are ordered in a way that if we process the schemas in that order, the previous schemas have already been processed.
3. Update the `order` field of each route in the `WorkflowRoutesCollection` according to the calculated topological order. 
4. check the workflows and the original schemas referred by the workflow routes exist in their corresponding collections.

#### User Journeys: Service Start-up

Service starts up and derives the output schemas for all workflow routes with empty output schemas. 

1. Validate the transformation configuration of the workflow routes.
2. Traverse the schemas in the transformation graph starting with the original schema, in topological order.For every route execute the following
   1. Retrieve the workflow of the corresponding `workflow_id` from the `WorkflowCollection`
   2. Retrieve the schema corresponding to the `input_schema_id` from the `WorkflowRoutesCollection`.
   3. Call metldata to execute the workflow on the input schema to compute the derived schema.
   4. Record the derived schema in the `SchemaCollection` and save its id to the `output_schema_id` of the WorkflowRoute.
3. If there are any errors / conflicts the service shall not start up.


#### User Journeys: Service Consumer Receives An Original AnnotatedEMPack

The transformation operation is triggered when the service consumer receives "original annotated Em Pack" or a “re-transform metadata” event.

1. Fetch the datapack ids and corresponding schema ids of all datapacks in the collection where the original_id field matches our original datapack id. Create a mapping of these schema ids to their datapack ids that we call “dirty map”, because all of these datapacks need to be either re-created or deleted.
2. Create a “transformed map” that maps schema ids to datapacks. This will hold the datapacks that have been transformed in this operation already. Initialize it with just the original schemapack id mapping to the original datapack.
3. Traverse the schemas in the transformation graph starting with the original schema, in topological order. For all of these schemas, do the following:
   1. Get a route that has the current schema as input. There can be multiple such routes at this point. In this case, for more stable results, we should select the route with the input schema with lowest order.
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
2. Recalculate the topological order of the workflow routes and update their `order` field
3. Re-compute the schemapacks of all transformed schemas
4. Re-run the transformations for all original datapacks

*QUESTION: How do we collect the changes all at once, do we wait for a certain time window after the first change is detected, or do we have a manual trigger to indicate that all changes are done and the configuration change operation can be triggered?

At this stage, the collections Workflows, Schemas and WorkflowRoutes are manually populated. How is the service going to be notified about the change? Is MOngoDB change stream relevant?*


### Not included:

- The service has no REST API to configure workflows but instead reads workflows from the database, where workflows must be stored in a predefined schema or format as required by the service.

- The service has no event consumer to populate its collection of known models but instead reads the models from a database where they have to be stored manually
