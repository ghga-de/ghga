# Preliminary Experimental Metadata (EM) Transformation Service (Question Mark Chrysalis)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

The goal of this epic is to implement a service for the transformation of Experimental Metadata (EM) from one representation/model to another. 
This service shall provide functionality around the configurable workflow concept from the `metldata` library to enable these transformations.
To this goal, it needs to keep track of the transformation workflows, original and derived datapacks/schemapacks and workflow routes in its database.


### Terminology

`Experimental Metadata (EM)`: Data describing the experimental process of generating the Research Data archived in GHGA.

`Experimental Metadata Ingress Models (EMIM)`: Schemas that define the structure and format of experimental metadata as it enters the GHGA system from external sources. Currently, GHGA supports only a single data ingress model for experimental metadata, which is the [ghga-metadata-schema](https://github.com/ghga-de/ghga-metadata-schema), but this epic is part of the effort to lift that restriction.

`Universal Discovery Model`: A common target representation to which all the EMs are transformed, serving as a basis for data queries and data display via the GHGA Data Portal. 

`EMPack`: Experimental metadata in datapack format. It follows a relational data schema corresponding to one of the EMIMs.

`AnnotatedEMPack`: A datapack enriched with additional information such as accessions that help integrate the EMPack into the archive.

`Workflow`: Instructions on how to produce a certain datapack/schemapack representation from another datapack/schemapack. The workflows are defined by the `metldata` library on which the transformation service will be built.

`Route`: Information on which specific workflow is used to produce datapack compliant with the output model when presented with datapack compliant with the input model.


### Included/Required:

- Implement a service that persists the annotatedEMPacks, workflows, and routes entities.
- Implement logic to process incoming AnnotatedEMPacks, execute the corresponding workflows and store the resulting AnnotatedEMPacks if required.
- Implement code to manage changes in models, workflows and routes, e.g. by creating universal schema descriptions from the ingress schema descriptions and re-transforming the AnnotatedEMPacks.


#### Core entities


`Model`

- purpose: describe the model entities used in the service

data structure:
```python
class Model(BaseModel):
   name: str
   description: str | None
   original: bool
   version: str | None
   schemapack: SchemaPack | None
   publish: bool 
   order: int | None

```

`Workflow`

- Purpose: holds a metldata-compatible workflow definition used to transform schemapacks/datapacks.

data structure:
```python
class Workflow(BaseModel):
   name: str
   description: str | None
   workflow: metldata.workflow.base.Workflow
```


`Route`

- Purpose: describe named routes that bind workflows, input schema types and produced output schema types, and whether outputs should be published.

data structure:

```python
class Route(BaseModel):
   name: str | None
   input_model_name: str
   output_model_name: str
   workflow_name: str
```

`Config`

- Purpose: model the current active transformation configuration version.

data structure:

```python

class BaseConfig(BaseModel):
   models: list[Model]
   workflows: list[Workflow]
   routes: list[Route]


class Config(BaseModel):
   version: int = 0  # used as identifier (always 0 in the first implementation)
   created: datetime # is the date when the config is validated and activated.
   config: BaseConfig
```


`AnnotatedEMPack`

Purpose: holds incoming and derived annotated EM datapacks that are to be processed or published.

data structure:

```python
class AnnotatedEMPack(BaseModel):
   id: uuid
   model_name: str  # the name of the corresponding `Model`
   original_id: str | None  # the id of the original incoming AnnotatedEMPack it was derived from
   datapack: DataPack
   annotation: dict
```

#### Implementation Details of Collections

The implementation of the EM transformation service will involve the following key components.

1. `models`
   
   Consists of Model objects
   * `name` is a unique human readable name of the schema also used as an identifier
   * `description` is a human readable description of the schema
   * `original` is a boolean flag indicating whether the schema is an original or derived schema
   * `version` is the version of the schema, initially None if it is not an original schema
   * `schemapack` is the schema in schemapack format, initially None if it is not an original schema
   * `publish` is a boolean flag indicating whether the AnnotatedEMPacks conforming to this schema should be published
   * `order` is the order in a topological ordering of the schemas in the transformation graph, initially None if not yet computed

   This collection is populated via a transformation configuration YAML file.

2. `workflows`

   Consists of Workflow objects
   * `name` is a unique human readable name for the workflow also used as an identifier. It should be a name indicating the purpose of the workflow for easier debugging and understanding of the operations.
   * `description` is a more verbose description of the workflow
   * `workflow` is the definition of the workflow in metldata format

   This collection is populated via a configuration YAML file that contains the defined ghga transformation workflows. 


3. `routes`

   Consists of Route object
   * `name` is a unique human readable name for the workflow route also used as an identifier. It must be calculated from the input and output schema names and the workflow name, e.g. `{input_model_name}:{workflow_name}:{output_model_name}`. 
   * `input_model_name` is the name/id of the input schema that the workflow route accepts
   * `output_model_name` is the name/id of the output schema that the workflow route produces 
   * `workflow_name` is a workflow name/id that is to be applied on a datapack / schemapack 
   

   This collection is populated via a configuration YAML file that contains the defined ghga workflow routes. 


4. `configs`

   Consists of a single document that holds the transformation configuration YAML. It defines the models, workflows, and routes. It is used to populate the `models`, `workflows`, and `routes` collections.


5. `AnnotatedEMPacks`

   Consists of AnnotatedEMPack objects.
   * `id` is a unique identifier for the AnnotatedEMPack
   * `model_name` is the unique name of the schemapack the EM datapack conforms to
   * `original_id` is the id of the original AnnotatedEMPack from which this AnnotatedEMPack was derived; it is None if this is an original AnnotatedEMPack
   * `datapack` is the EM in datapack format that conforms to the schemapack identified by `model_name`
   * `annotation` is an annotation object with information from other models held by the service

   This collection is filled from two sources: incoming events from the GHGA Study Repository and outputs of workflow routes executed by the EM Transformation Service.

   Note that we only store published datapacks on the collection. If there are intermediate transformed datapacks, they will only be created and kept in memory as long as they are needed for running a full transformation graph corresponding to a single original datapack.

#### Transformation Configuration

A transformation is configured through the models, workflows and routes collections. The current configuration of the service is read from a YAML file and stored as a global `Config` object that is later used to determine whether a configuration change has occurred.

Routes define the transformation workflows to transform an input schemapack to an output schemapack. Each route specifies which workflow to apply to a given input schemapack and what output schemapack it is expected to produce.

Routes also define a a graph structure where schemapacks are nodes and routes are directed edges. The source nodes of this graph are the “original schemapacks” (aka EMIMs) defined as SchemaPack. The graph must not contain any "diamonds", i.e. there must be at most one directed path between any two schemapacks in the graph. This also implies that the graph does not contain any cycles, i.e. is a directed acyclic graph (DAG). 

We enforce that stronger unique-path property of the graph because "diamond" shapes indicate that there is unnecessary redundancy in the graph that should be avoided, and since it leaves no ambiguity in how datapacks are transformed.

This graph structure is used to validate the transformation configuration and to determine the order in which schemapacks need to be processed during service startup and when processing incoming AnnotatedEMPacks.

#### Transformation Configuration Validation

Transformation configuration validation includes:

1. Check the workflows and the original schemapacks referred by the routes exist in their corresponding collections.
2. Check that the schemapacks marked as `original` are not referred as route output schemapacks.
3. Validate the schemapacks using SchemaPack library and workflows using the metldata library.
4. Check the graph conforms to the unique path requirement mentioned above, and thereby also that it does not contain cycles.
5. Calculate the topological order of the nodes in the graph using an algorithm similar to Kahn's algorithm, so that the schemapacks are ordered in a way that if we process the schemapacks in that order, the previous schemapack have already been processed.
6. Update the `order` field of each schemapack in the `models` according to the calculated topological order. 


#### User Journeys: Model Derivation

When manually triggered, the service derives the output schemapacks for all routes with empty output schemapacks. The same set of operations is also triggered when the configuration changes.

1. Validate the transformation configuration of the workflow routes.
2. Traverse the schemapacks in the transformation graph starting with the original schemapack, in topological order. For every route execute the following:
   1. Retrieve the workflow of the corresponding `workflow_name` from the `Workflows`
   2. Retrieve the schemapack corresponding to the `input_model_name` from the `routes`.
   3. Call metldata to execute the workflow on the schemapack of the input schema to compute the schemapack for the derived schema.
   4. Update the schemapack field of the Model corresponding to the `output_model_name` of the Route with the output of step 3.
3. If there are any errors / conflicts, the operation shall fail and report the error.


#### User Journeys: Service Consumer Transforms An Original AnnotatedEMPack

The transformation operation is triggered when the service consumer receives an upsertion of an "original AnnotatedEMPack" or a “re-transform AnnotatedEMPack” event.

1. Fetch the datapack ids and corresponding schemapack names of all datapacks in the AnnotatedEMPacks collection where the `original_id` field matches our original datapack id. Create a mapping of these schemapack names to their datapack ids that we call “dirty map”, because all of these datapacks need to be either re-created or deleted.
2. Create a “transformed map” that maps schemapack names to datapacks. This will hold the datapacks that have been transformed in this operation already. Initialize it with just the original schemapack names mapping to the original datapack.
3. Traverse the schemapacks in the transformation graph starting with the original schemapack, in topological order. For all of these schemapacks, do the following:
   1. Get the route that has the current schemapack as input. Since we require the unique-path-property, there should be exactly one such route. Raise an error if this is not the case (should never happen if the traverse correctly and the graph was properly validated).
   2. Get the datapack from the “transformed map” that corresponds to the input schemapack of that route. This is the “input datapack” for this step. It should always exist at this point if the topological order was computed correctly, and we can raise an error at this point if this is not the case.
   3. Compute the transformed datapack using the input datapack and the workflow route.
   4. If the current schemapack name is in the “dirty map”, remove it there and update the “transformed map” with the transformed datapack.
   5. Otherwise, add the transformed datapack to the “transformed map” with a newly generated id, setting its `model_name` to the current schemapack name, and its original_id field to the original datapack id.
4. Finally, upsert all entries in the “transformed map” to the database that should be published, and delete all remaining entries in the “dirty map” from the database.

This course of action avoids deleting “dirty” datapacks while they are recreated, since that would make the corresponding resources disappear while the transformation is ongoing. It also keeps any intermediate datapacks in memory, avoiding unnecessary database operations and operations.

#### User Journeys: Configuration Change

The “configuration change” operation should be triggered after detecting a change in the configuration YAML file.

The transformation change is detected by comparing the current configuration with the configuration stored in the `configs` collection. If there is a difference, the new transformation configuration is set as the current configuration and the service performs the re-computation of derived schemapacks and re-transformation of all original AnnotatedEMPacks.

The configuration change will trigger the following operations:
1. Re-compute the schemapacks of all transformed schemapacks as described in the "Model Derivation" user journey
2. Re-run the transformations for all original datapacks as described in the "Service Consumer Transforms An Original AnnotatedEMPack" user journey.


### Not included (but possible future extensions):

- A REST API to retrieve the currently used public schemapacks, which would be useful for frontend developers for inspection purposes.
- A REST API to push configuration data instead of loading it from YAML files at startup.
- Configuration versioning to maintain a full history of changes and enable rollbacks to previous versions.
