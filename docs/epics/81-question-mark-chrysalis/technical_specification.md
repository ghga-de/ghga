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

`Universal GHGA Model`: Also referred as `EMModel`. A schema that defines how to represent experimental metadata within the GHGA ecosystem.

`EMPack`: Experimental metadata in datapack format. It follows a relation data schema and compatible with one of the Universal GHGA Models. 

`AnnotatedEMPack`: A datapack enriched with an additional information. 

`AnnotatedEMPackCollection`: A MongoDB collection of AnnotatedEMPack objects.

`TransformationWorkflow`: Instructions on how to produce a certain data/model representation from another data/model.

`TransformationWorkflowCollection`: A MongoDB collection of TransformationWorkflow objects.

`WorkflowRoute`: Information on which specific workflow is used to produce data compliant with the output model when presented with data compliant with the input model.

`WorkflowRoutesCollection`: A MongoDB collection of WorkflowRoute objects.


### Included/Required:

- Implement logic to process incoming AnnotatedEMPacks, execute the corresponding workflows and store the resulting AnnotatedEMPacks if required.
- Implement service start-up logic to derive missing schemas for workflow routes with empty output schemas.
- Implement MongoDB collections to store AnnotatedEMPacks, TransformationWorkflows and WorkflowRoutes.

#### Collections

`AnnotatedEMPackCollection`

Purpose: store incoming and derived annotated EM datapacks that are to be processed or published.

data structure:
```python
class AnnotatedEMPack(BaseModel):
   workflow_route_name: str
   data: Dict[str, Any]  # Example: {"sample_id": "S123", "experiment_type": "RNA-seq", ...}
```


`TransformationWorkflowCollection`

- Purpose: store metldata-compatible workflow definitions used to transform schemas/data.

data structure:
```python
class TransformationWorkflow(BaseModel):
   workflow_id: PyObjectId = Field(..., alias="_id")
   workflow_definition: Dict[str, Any] = Field(default_factory=dict)
```


`WorkflowRoutesCollection`

- Purpose: describe named routes that bind workflows, input schema types and produced output schemas, and whether outputs should be published.

```python
class WorkflowRoute(BaseModel):
   id: Optional[PyObjectId] = Field(default=None, alias="_id")
   workflow_route_name: str
   workflow_id: PyObjectId
   workflow_input_schema_type: str
   workflow_output_schema: Dict[str, Any] = Field(default_factory=dict)
   publish: bool
```


#### Implementation Details of Collections

The implementation of the EM transformation service will involve the following key components:


1. `AnnotatedEMPackCollection`

   Consists of AnnotatedEMPack objects that is a tuple of `workflow_route_name` and `data`  
   * `data` is an `AnnotatedEMPack` object that is to be transformed
   * `workflow_route_name` is the name of the workflow route that consumes this data

   This collection is filled from two sources: incoming events (FROM?) and outputs of executed workflow routes.

2. `TransformationWorkflowCollection`

   Consists of TransformationWorkflow objects that is a tuple of `workflow_id` and `workflow_definition`  
   * `workflow_id` is an identifier for a workflow  
   * `workflow_definition` is the definition of the workflow in compliance with metldata. 

   This collection is populated manually with the defined ghga transformation workflows.

3. `WorkflowRoutesCollection`

   Consists of WorkflowRoute objects that is a tuple of (`workflow_route_name`, `workflow_id`, `workflow_input_schema_type`, `workflow_output_schema`, `publish`)  
   * `workflow_route_name` is a unique name for a route.  
   * `workflow_id` is a workflow identifier that is to be applied on a data / schema  
   * `workflow_input_schema_type` is the type of a schema that the workflow route can consume
   * `workflow_output_schema` is the schema that the workflow route produces  
   * `publish` is a boolean flag indicating whether the output of the workflow route shall be published in form of an AnnotatedEMPack to AnnotatedEMPack collection.

   This collection is populated manually with the defined ghga workflow routes.  
   An empty workflow_output_schema indicates the route requires schema derivation at startup.  

   **Storing Universal GHGA Models in the WorkflowRoutesCollection:**

   WorkflowRoutesCollection will also be used to store universal GHGA models.  
   When storing a universal GHGA model in the Workflow route collection, the `workflow_id` will be Null and `workflow_input_schema_type` will be an empty dictionary.  
   The `workflow_route_name` will contain the name of the universal GHGA model and the `workflow_output_schema` will store the schema of the universal GHGA model. 

   | workflow_route_name     | workflow_id   | workflow_input_schema_type | publish | workflow_output_schema                                                                                                                               |
   | ----------------------- | ------------- | -------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
   | universal_ingress_model |               |                            | False   | {...schema of universal ingress model...}                                                                                                            |
   | universal_accession     | add_accession | universal_ingress_model    | True    | initially `{}` (empty dictionary as a placeholder); upon completion of computing all the derived schemas {...schema of universal accession model...} |



#### User Journeys

1. Service starts up and derives the output schemas for all workflow routes with empty output schemas. 
   1. All applicable WorkflowRoutes are retrieved from the WorkflowRoutes collection.  The applicable workflows are the ones whose `workflow_output_schema` is empty.
   2. For every applicable WorkflowRoute:
      1. The service retrieves the workflow of the corresponding `workflow_id` from the `TransformationWorkflowCollection`
      2. The service retrieves the schema corresponding to the `workflow_input_schema_type` from the `WorkflowRoutesCollection`.
      3. Call metldata to execute the workflow on the input schema to compute the derived schema.
      4. Record the derived schema in the `workflow_output_schema` of the WorkflowRoute.
   3. If there are any errors / conflicts the service shall not start up.
   4. Circular dependencies in the workflow routes are detected by analyzing the workflow route graph for cycles; if any cycles are found, the service startup fails with an error indicating the circular dependency.
2. An AnnotatedEMPack is created in the `AnnotatedEMPackCollection`
   1. The service uses polling at regular intervals to check the DB for new AnnotatedEMPacks in the `AnnotatedEMPackCollection` that are not yet processed.
   2. The service identifies an unprocessed AnnotatedEMPack from the collection.
   3. The service retrieves the WorkflowRoute that matches the `workflow_route_name` of the incoming AnnotatedEMPack.
   4. The service executes the workflows of all the retrieved WorkflowRoutes on the `data` of the incoming AnnotatedEMPack.
   5. Marks the AnnotatedEMPack as processed after the execution of the workflow by updating a status field (e.g., `status: "processed"`) in the AnnotatedEMPackCollection.
   6. The output AnnotatedEMPack is stored in the AnnotatedEMPack collection if the workflow route has `publish` set to True.



### Not included:

- The service has no REST API to configure workflows but instead reads workflows from the database, where workflows must be stored in a predefined schema or format as required by the service.

- The service has no event consumer to populate its collection of known models but instead reads the models from a database where they have to be stored manually
