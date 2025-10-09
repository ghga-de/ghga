# Preliminary Experimental Metadata (EM) Transformation Service (Question Mark Chrysalis)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

Implement a service that is responsible for the transformation of Experimental Metadata (EM) from one representation (model) to another. It imports the transformation and workflow functionalities of the library `metldata` to carry out the transformations.


### Included/Required:

#### Collections

The service will have 3 collections:

1. AnnotatedEMPack collection: AnnotatedEMPack is a tuple of `type` and `data` where `type` is the `route_name` and `data` is the actual experimental metadata in datapack format. Hence, this is a collection of AnnotatedEMPack objects. This collection is filled from two sources: incoming events (FROM?) and outputs of executed workflow routes.

2. Transformation Workflow collection: Workflows as defined in compliance with metldata. A workflow consumes generic annotations, data and a schema, executes a series of transformation steps and produces derived data and schema.

3. WorkflowRoutes collection: Workflow route consists of literal routes between the transformed models e.g., it defines the route required to transform model A into model B.
   WorkflowRoute is a tuple of (`route_name`, `workflow_id`, `workflow_input_schema_type`, `publish`) where

   * `route_name` is a unique name for a route. 

   * `workflow_id` is an identifier for a workflow that can be applied on this data / schema
  
   * `workflow_input_schema_type` is the name of the type of schema (`emim-schema-id`) that the workflow route can consume (old name: input_type)

   * `workflow_output_schema` is the schema that the workflow route produces (old name: schema)
  
      Note: There is no separate EMIM collection. The models will be a part of the WorkflowRoutes collection.

   * `publish` is a boolean flag indicating whether the output of the workflow route shall be published in form of an AnnotatedEMPack to AnnotatedEMPack collection.

   When storing a universal GHGA model in the Workflow route collection, the `workflow_id` and `workflow_input_schema_type` will be empty. The `route_name` will be the name of the universal GHGA model and the `workflow_output_schema` will be the schema of the universal GHGA model. 

   | route_name              | workflow_id   | workflow_input_schema_type | publish | workflow_output_schema                                                                                     |
   | ----------------------- | ------------- | -------------------------- | ------- | ---------------------------------------------------------------------------------------------------------- |
   | universal_ingress_model |               |                            | False   | {...schema of universal ingress model...}                                                                  |
   | universal_accession     | add_accession | universal_ingress_model    | True    | first {}; upon completion of computing all the derived schemas {...schema of universal accession model...} |



#### Service Start-up

1. When started up
   1. All applicable WorkflowRoutes are retrieved from the WorkflowRoutes collection. The applicable workflows are the ones whose `workflow_output_schema` is empty.
   2. For every applicable WorkflowRoute:
      1. The service retrieves the workflow of the corresponding `workflow_id` from the Transformation Workflow collection.
      2. The service retrieves the schema corresponding to the `workflow_input_schema_type` from the WorkflowRoutes collection.
      3. Call metldata to execute the workflow on the input schema to compute the derived schema.
      4. Record the derived schema in the `workflow_output_schema` of the WorkflowRoute.
   3. If there are any errors / conflicts the service shall not start up.
   4. Circular dependencies in the workflow routes are detected by analyzing the workflow route graph for cycles; if any cycles are found, the service startup fails with an error indicating the circular dependency.
2. When an AnnotatedEMPack is received:
   1. The service checks the `type` of the incoming AnnotatedEMPack and retrieves all WorkflowRoutes where the `route_name` matches the `type` of the incoming AnnotatedEMPack.
   2. The service executes the workflows of all the retrieved WorkflowRoutes on the `data` of the incoming AnnotatedEMPack.
   3. The output AnnotatedEMPack is stored in the AnnotatedEMPack collection if the workflow route has `publish` set to True.
####  Processing Annotated Experimental Metadata

### Not included:

- The service has no REST API to configure workflows but instead reads workflows from the database, where workflows must be stored in a predefined schema or format as required by the service.

- The service has no event consumer to populate its collection of known models but instead reads the models from a database where they have to be stored manually
