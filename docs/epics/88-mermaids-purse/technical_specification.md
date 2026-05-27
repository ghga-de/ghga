# Global Unique IDs, Aggregate Transformations, and Workflow API (Mermaid's Purse)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope

### Outline

This epic delivers six related improvements to the schemapack/metldata ecosystem and the em-transformation-service:

1. **Schemapack GUID support** — an opt-in `globallyUniqueIds` flag in the schemapack schema enforces globally unique resource IDs across all classes in validated datapacks.
2. **Metldata transformation additions** — `duplicate_class` is retained; the new `add_class` transformation is added to support the aggregate stats workflow.
3. **Metldata aggregate stats workflow** — the aggregate stats workflow is rewritten using the new GUID-compatible transformations.
4. **Metldata `WorkflowRunner` API** — `WorkflowHandler` is refactored to separate model derivation from data transformation. A new public `WorkflowRunner` class and a `validate_workflow` convenience function are added.
5. **`jsonsubschema` fork** — `jsonsubschema` is forked under the GHGA organisation to ship a bug fix for enum values containing regex metacharacters.
6. **em-transformation-service updates** — the service adopts `WorkflowRunner` to replace its manual transformation loop.

### Terminology

`Global Unique ID (GUID)`: A resource identifier unique not just within a single class but across all classes in a schemapack schema. GHGA accessions are an example: every Study, Sample, Dataset, etc. receives a globally unique accession.

`Model Derivation`: Running a workflow's transformation steps on an input schema to produce the output schema.

`Data Transformation`: Running a workflow's transformation steps on a datapack to produce a transformed datapack.

`Transformation Registry`: A mapping from transformation names to their `TransformationDefinition` objects. It is the authoritative lookup table used when resolving workflow step names to executable transformations.

`WorkflowRunner`: The new high-level public class in metldata that executes a workflow. It accepts `workflow` and `input_model` at construction, eagerly derives the output schema (exposed via `.model`), and defers data transformation to `.run_workflow(data, annotation)` calls.

`Aggregate Stats Workflow`: A GHGA-specific metldata workflow that produces a representation of the GHGA ingress model optimised for aggregate statistics queries.

`Universal Discovery Model (UDM)`: The common target schema to which all EMIMs are transformed, serving as the basis for data queries and display in the GHGA Data Portal.

`Persisted Administrative Metadata (PAM)`: A set of classes (e.g., `Study`, `Dataset`, `Publication`) representing administrative metadata that are not a part of the experimental EMIM, and included in the annotations published by the study-registry-service.

`EMIM file classes`: The five file classes in the experimental schema: `ResearchDataFile`, `ProcessDataFile`, `IndividualSupportingFile`, `ExperimentMethodSupportingFile`, and `AnalysisMethodSupportingFile`.

### Included/Required

#### 1. SchemaPack

##### 1.1. Globally Unique IDs Support

Schemapack supports an opt-in `globallyUniqueIds` boolean flag at the schema level. When `true`, every resource ID across every class in a conforming datapack must be unique. The flag defaults to `false`, preserving backwards compatibility.

**Schema definition**

```yaml
schemapack: 5.0.0
globallyUniqueIds: true   # opt-in; default false
description: "Schema with globally unique resource IDs (GHGA accession model)"
classes:
  Study:
    id:
      propertyName: accession
    content: content_schemas/Study.schema.json
  Sample:
    id:
      propertyName: accession
    content: content_schemas/Sample.schema.json
```

**Datapack validation**

When validating a datapack against a schema with `globallyUniqueIds: true`:

1. Build a dict `{resource_id: [class_name, ...]}` by iterating over every class and collecting the class names for each resource ID.
2. Filter for entries with more than one class — these are the collisions.
3. For each collision, raise a validation error naming the conflicting resource ID and every class in which it appears.

##### 1.2. Serialization Fix (Frozen Dicts / Circular Reference)

Schemapack's serialization of `DataPack` objects (which use frozen dicts internally) currently raises `ValueError: Circular reference detected (id repeated)` in client code. The fix shall be applied inside schemapack so that no client-side workarounds are required.

#### 2. Metldata

##### 2.1. `duplicate_class` Compatibility with Global Unique IDs

This section does not include any changes to `duplicate_class` itself, which continues to function as it currently does. It only clarifies how the presence of `globallyUniqueIds` in the schema affects the validation of workflow outputs that use `duplicate_class`.

The `duplicate_class` transformation shall be retained in the transformation registry; the `globallyUniqueIds` constraint does not conflict with its presence. There are two scenarios to consider:
1. The final output schema does not have `globallyUniqueIds` set. The `duplicate_class` transformation works as it currently does, with no issues.
2. The final output schema has `globallyUniqueIds: true`. If a workflow duplicates a class and later deletes it, the final output contains no ID collision. Transient ID collisions introduced by `duplicate_class` within a workflow are permitted — the `globallyUniqueIds` constraint is enforced only on the final workflow output, not on intermediate steps.

The second scenario is consistent with the existing metldata behaviour: when the no-intermediate-validation flag is set, model compatibility is not enforced after every step — only at the workflow boundaries. The `globallyUniqueIds` uniqueness constraint follows the same rule: it is enforced only at **workflow output validation** (the final step), not during intermediate steps. If the output schema of a workflow still has `globallyUniqueIds: true` and the output datapack contains duplicate IDs across classes, the post-workflow validation raises an error at that point.

Two test cases should be added to ensure:
1. When no-intermediate-validation flag is set, a workflow that uses `duplicate_class` and produces a final schema with `globallyUniqueIds: true` does not raise an error given that the output datapack has no ID collisions across classes.
2. When intermediate validation is enabled, the same workflow raises an error at the step where `duplicate_class` is applied, since the intermediate schema at that point contains duplicate IDs across classes.


##### 2.2. Implications of Globally Unique IDs in Transformation Workflows

In GHGA, the ingress schema does not enforce globally unique IDs: submitters may reuse the same alias across multiple classes as long as each alias is unique within its class. The aggregate stats workflow must produce a derived schema that enforces globally unique IDs, because the UDM uses GHGA accessions — which are globally unique — as resource IDs.

To bridge this constraint change between input and output schemas, the `replace_resource_ids` transformation shall be extended with an optional `globally_unique_ids` argument:

```yaml
class_name: File
globally_unique_ids: true
```

This argument defaults to `false`. When set to `true`, the transformation sets `globallyUniqueIds: true` on the output schemapack. No additional validation logic is required: the post-transformation step validates the output automatically.

##### 2.3. `add_class` Transformation


The need for the `add_class` transformation comes from the new design of the metadata schema, which removed administrative metadata from the current schema. The classes removed are: 
1. `Study`, 
2. `Publication`, 
3. `Dataset`, 
4. `DataAccessPolicy`, and 
5. `DataAccessCommittee`. 

This also results in removing the `dataset` property from the EMIM file classes.

This necessitates merging the Persisted Administrative Metadata (PAM) back into the EMIM before transforming it into the UDM via the aggregate stats workflow. PAM will be part of the annotations published by the study-registry-service.

**Assumptions**

- The class being added will not exist in the schema.
- If the newly added class has a relation, the target class of that relation must exist in the schema.

**Configuration model**

```python
class AddClassConfig(BaseModel):
    class_name: str                                    # PascalCase; must not already exist in the schema
    id_property_name: str                              # the property used as the resource ID
    content_schema: dict                               # a valid JSON Schema object for the class content
    description: str | None = None
    relations: list[Relation] | None = None                 # optional list of relations from the new class to existing classes


class Relation(BaseModel):
    relation_name: str
    description: str | None = None
    target_class: str
    target_resource_id_field: str                       # the property in the target class used to reference the target resource ID
    mandatory: MandatoryRelationSpec
    multiple: MultipleRelationSpec
```

**Model transformation**

- Add the new `ClassDefinition` (with content schema and any declared relations) to the schemapack.
- Raise `ModelAssumptionError` if a class with `class_name` already exists.
- Raise `ModelAssumptionError` if any `target_class` in `relations` does not exist in the schema.

**Data transformation**

For the class declared in `config.class_name`, the transformation inserts the resources sourced from the PAM into the DataPack. Each PAM resource is processed individually and split into two parts before being written:

- **Content** — properties that match the JSON Schema declared in `config.content_schema` are kept under the resource's content.
- **Relations** — for every entry in `config.relations`, the property named by `target_resource_id_field` is read from the incoming PAM record, removed from content, and written as a relation under `relations.<relation_name>` with `targetClass = target_class` and `targetResources` set to the value(s) read.
- **Resource ID** — taken from the PAM record under the name given by `config.id_property_name` and used as the key under `resources.<class_name>`.

##### 2.4. `infer_relation_from_content` Transformation

The need for the `infer_relation_from_content` transformation comes from the new design of the metadata schema. After the `add_class` transformation re-introduces `Dataset` into the EMIM, the `Dataset` content carries a flat list of file resource IDs under the `files` property. These IDs span the EMIM file classes. The dataset back-reference that used to exist on each of these file classes must be reconstructed before the aggregate stats workflow can run path inferences such as `Dataset<(dataset)ResearchDataFile…`.

This transformation walks the flat ID listing on a source class, resolves each ID to the file class it belongs to, and writes a relation pointing back to the source class on the resolved resource. It differs from infer_relation in that the source of the link information is a content property holding resource IDs, not an existing relation path.

**Assumptions**

- The source class declared in the configuration must exist in the schema and must declare the content property holding the ID listing.
- The candidate target classes declared in the configuration must exist in the schema.
- The relation name declared in the configuration must not already exist on any of the candidate target classes.
- Each resource ID held by the source content property must resolve to a resource in exactly one of the candidate target classes. An unresolvable ID, or an ID present in more than one candidate class, is a data transformation error.

**Configuration model**

```python
class InferRelationFromContentConfig(BaseModel):
    source_class: str                          # class holding the ID listing (e.g. Dataset)
    source_content_property: str               # name of the property on source_class holding the flat list of IDs
    new_relation_name: str                     # name of the relation to add on each resolved target resource
    target_classes: list[str]                  # candidate classes where the listed IDs may be resolved
    description: str | None = None
    mandatory: MandatoryRelationSpec
    multiple: MultipleRelationSpec
```

See the [Appendix](#appendix-pam-transformation-configurations) for the concrete configuration used in the aggregate stats workflow.
**Model transformation**

- For each class in `config.target_classes`, add a relation declaration named `config.new_relation_name` with `targetClass = config.source_class` and `mandatory`/`multiple` from the configuration.
- The source class is not modified; the content property listing the IDs is left in place.
- If the listing is no longer wanted in the final output, remove it with a subsequent `transform_content` step.

**Data transformation**

The transformation first builds a global mapping from each ID listed under `source_content_property` to the set of source resources that reference it. Iterating `resources.<source_class_name>` once produces:

```
file_id_1 → [DS_A, DS_B]
file_id_2 → [DS_A]
file_id_3 → [DS_B, DS_C]
...
```

- The keys of this mapping are intersected with the resource IDs present under `resources.<class_name>` for the class being processed. For each ID in the intersection, the corresponding set of source resource IDs is written to `relations.<relation_name>.targetResources` on that resource.
- IDs outside the intersection belong to other classes and are left untouched — they will be picked up by their own invocations.

##### 2.5. Aggregate Stats Workflow: Adding Back PAM Classes via `add_class`

The classes that will be added back to the EMIM via the aggregate stats workflow are 
1. `Study`, 
2. `Publication`, 
3. `Dataset`. 

`Dataset` will have `DataAccessCommittee` and `DataAccessPolicy` inlined, so they will not appear as separate classes in the intermediate or final schema. The full `add_class` configurations for these classes are in the [Appendix](#appendix-pam-transformation-configurations).

##### 2.6. `WorkflowRunner` — Separated Model and Data Transformation

**Problem**

Third-party services (e.g., em-transformation-service) currently interact with `TransformationHandler` directly:

```python
# Current third-party code — leaks internals
for step in workflow.workflow.operations:
    transformation_def = self._transformation_registry[step.name]
    typed_config = transformation_def.config_cls.model_validate(step.args)
    handler = TransformationHandler(
        transformation_definition=transformation_def,
        transformation_config=typed_config,
        input_model=current_schema,
    )
    current_data = handler.transform_data(current_data, annotation)
    current_schema = handler.transformed_model
```

This couples model derivation and data transformation in one loop. The em-transformation-service needs them separate: it derives all output schemas once at startup, then transforms datapacks individually at runtime.

**Solution: Refactor `WorkflowHandler` and introduce `WorkflowRunner`**

1. `WorkflowHandler`:
   
`WorkflowHandler` is restructured so that model derivation and data transformation become two distinct phases:

- **`__init__`**: walks the workflow once, builds a `WorkflowStepHandler` and derives the output schema for each step via `TransformationHandler`, and stores the `TransformationHandler` instances internally. The final output schema is exposed as an attribute.
- **`run()`**: iterates over the cached `TransformationHandler` instances, applies data transformations in order, and returns a `DataPack` directly. `WorkflowResult` (which previously bundled model and data) is removed.
- Boundary validation is preserved: input schema/data is validated against the first step's assumptions; output schema/data is validated against the last step's output model.

2. `WorkflowRunner`:

- Location: `src/metldata/workflow/run.py`
- Accepts `workflow` and `input_model` as keyword arguments at construction; registry-aware.
- **`__init__`**: eagerly derives all intermediate schemas; exposes the final schema via the read-only `.model` property.
- **`run_workflow(data, annotation)`**: applies data transformations using the cached `TransformationHandler` instances; may be called once per datapack without re-deriving schemas.

3. `validate_workflow()`:

- Location: `src/metldata/workflow/validate.py`
- Convenience wrapper that delegates to `validate_workflow_against_registry` using the built-in registry so callers do not need to pass a registry explicitly.

###### Public API Surface

The following are the stable public exports from `metldata.__init__`:

| Name                | Kind     | Purpose                                                     |
| ------------------- | -------- | ----------------------------------------------------------- |
| `WorkflowRunner`    | class    | High-level workflow execution; `.model` + `.run_workflow()` |
| `validate_workflow` | function | Validates a workflow against the built-in registry          |



##### 2.7. Aggregate Stats Workflow Integration Test

An end-to-end integration test shall be added to metldata exercising all new capabilities together: a `globallyUniqueIds` schema, `add_class` (pending resolution of open questions in section 2.5), correct error behaviour for `duplicate_class` when intermediate validation is enabled, and `WorkflowRunner` running model derivation and data transformation independently.

The test uses a representative aggregate stats workflow and verifies that the `globallyUniqueIds` constraint is enforced on the output: validation rejects datapacks with duplicate IDs across classes.


##### 2.8. Performance Benchmark of the Aggregate Stats Workflow

A performance benchmark shall be run against the full EMIM → aggregate stats workflow using the Epignostix dataset as a representative input. Profiling is done via `cProfile`. The goal is to establish a baseline transformation time before production deployment. Results are attached to the epic. Any step that accounts for a disproportionate share of total time is flagged for investigation.


#### 3. em-transformation-service: Adopt `WorkflowRunner`

The em-transformation-service currently drives workflow execution by manually iterating over transformation steps and managing `TransformationHandler` instances. This must be replaced with `WorkflowRunner`.

- **`model_derivation.py`**: replace the manual step loop with `WorkflowRunner(workflow=..., input_model=input_schema)`; read the output schema via `runner.model`.
- **`aem_pack_registry._apply_workflow_to_data`**: replace the manual step loop with `runner.run_workflow(data=data, annotation=annotation)`.
- After the change: the service no longer imports `TransformationHandler`, manages intermediate schema state, or resolves transformation names from the registry directly. A `WorkflowRunner` instance is constructed once per route at config-validation time and reused for all data transformations on that route.


#### 4. `jsonsubschema` Enum Bug Fix

Metldata depends on `jsonsubschema` (IBM) for JSON Schema subset validation. The library is unmaintained and contains a known bug: in `_canonicalization.py`, enum values are converted to regex patterns via bare string concatenation (`"^" + str(x) + "$"`) without escaping regex metacharacters. Enum values containing characters such as `+`, `*`, or `.` are therefore misinterpreted as regex operators, producing incorrect validation results.

This bug manifested against the GHGA `instrument_model` controlled vocabulary: the enum value `454_GS_FLX+` generates the unescaped pattern `^454_GS_FLX+$`, which matches `454_GS_FLXXX` rather than the literal string. The upstream fix is captured in [IBM/jsonsubschema@8e6535](https://github.com/IBM/jsonsubschema/commit/8e6535461d00f37e4c06189826d320e4750d3a31).

Since upstream maintainers are unresponsive, the solution is to **fork `jsonsubschema` under the GHGA organisation** and publish a GHGA-maintained release. Steps:

1. Fork `IBM/jsonsubschema` to `ghga-de/jsonsubschema`.
2. Apply the fix from [IBM/jsonsubschema@8e6535](https://github.com/IBM/jsonsubschema/commit/8e6535461d00f37e4c06189826d320e4750d3a31).
3. Tag and publish a release from the fork.
4. Update metldata's dependency to reference the GHGA fork.
5. Add a regression test to metldata using the specific GHGA CV value that triggers the bug; the test must fail without the fix and pass with it.

**Note:** `jsonsubschema` only supports JSON Schema draft 4. The GHGA metadata schema uses draft 2019-09, so keywords like `$defs` and `unevaluatedProperties` are silently ignored or mishandled. Upgrading the library to support draft 2019-09 is out of scope for this epic; it is tracked as a parallel side task and has already been claimed by a team developer.

## User Journeys

### Journey 1: Schema Designer Enables Globally Unique IDs

1. A schema designer adds `globallyUniqueIds: true` to the schema YAML.
2. Running `schemapack validate` against a conforming datapack succeeds only if all resource IDs are distinct across all classes.
3. If a collision exists — e.g., both a Study and a Sample have the ID `GHGAS00001` — validation fails with a clear error naming the conflicting ID and both classes.

### Journey 2: Workflow Author Builds an Aggregate Stats Workflow with `add_class`

1. A workflow author designing the EMIM → UDM workflow needs to reintroduce administrative classes (e.g., `Study`, `Dataset`) that are absent from the experimental EMIM but present in PAM annotations.
2. The author adds an `add_class` step specifying the class name, `id_property_name`, content JSON Schema, and any relations to existing classes.
3. Subsequent steps (e.g., `infer_relation_from_content`) reconstruct relations between the new class and existing resources.
4. The workflow validates with `validate_workflow(workflow)` without errors.
5. `WorkflowRunner(workflow=workflow, input_model=emim_schema).model` produces the derived schema with the new class present.

### Journey 3: em-transformation-service Derives Models and Transforms Data Independently

1. At startup, for each route the service constructs `WorkflowRunner(workflow=..., input_model=input_schema)` to derive the output schema. No datapacks are required at this stage.
2. The derived schema is exposed via `runner.model`, stored alongside the route, and used to validate incoming data.
3. When an `AnnotatedEMPack` arrives, the service calls `runner.run_workflow(data=data, annotation=annotation)` to produce the derived datapack — without managing `TransformationHandler` instances or intermediate schema state.
4. The resulting datapack is validated against the pre-derived output schema and published.

## Additional Implementation Details

- `globallyUniqueIds` defaults to `false`. No existing schemapack or datapack needs modification.
- `WorkflowRunner` eagerly derives all intermediate schemas at construction time. `.run_workflow()` only applies data transformations using the cached `TransformationHandler` instances. The two operations are fully independent: `.model` may be accessed without ever calling `.run_workflow()`, and vice versa.
- Boundary validation is preserved: input schema/data is validated against the first step's assumptions; output schema/data is validated against the last step's output model.
- `WorkflowRunner` embeds the built-in transformation registry. Callers that need a custom registry (e.g., for testing) can supply one explicitly.
- The serialization fix for frozen dicts should be shipped as a patch release of schemapack before or alongside the main changes in this epic.


### Not Included

- `delete_relation` transformation — not required for the current aggregate workflow.
- `jsonsubschema` upgrade to support JSON Schema draft 2019-09 or later.
- The changes to the ghga-metadata-schema


## Human Resource/Time Estimation

Number of sprints required: 3

Number of developers required: 2

## Appendix: PAM Transformation Configurations

### `add_class`

#### Study

```yaml
class_name: Study
description: "A Study class added back to the EMIM via add_class transformation"
id_property_name: accession
content_schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "additionalProperties": false,
    "description": "A Study.",
    "properties": {
      "title": { "type": "string" },
      "description": { "type": "string" },
      "types": { "type": "array", "items": { "type": "string" }},
      "affiliations": { "type": "array", "items": { "type": "string" }}
    },
    "required": ["title", "description", "types", "affiliations"],
    "type": "object"
  }
```

#### Publication

The `Publication` published via study-registry-service carries a `study_id` attribute, which the `add_class` transformation uses to create a relation from `Publication` to `Study`.

```yaml
class_name: Publication
description: "A Publication class added back to the EMIM via add_class transformation"
id_property_name: accession
content_schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "additionalProperties": false,
    "description": "A Publication.",
    "properties": {
      "title": { "type": "string" },
      "abstract": { "type": ["string", "null"] },
      "authors": { "type": "array", "items": { "type": "string" } },
      "year": { "type": "integer" },
      "journal": { "type": ["string", "null"] },
      "doi": { "type": ["string", "null"] }
    },
    "required": ["title", "authors", "year"],
    "type": "object"
  }
relations:
  - relation_name: study
    description: "A relation from Publication to Study."
    target_class: Study
    target_resource_id_field: study_id
    mandatory: MandatoryRelationSpec # placeholder; defined during implementation
    multiple: MultipleRelationSpec # placeholder; defined during implementation
```

#### Dataset

`DataAccessCommittee` and `DataAccessPolicy` are inlined into the `Dataset` content schema. The `files` property holds a flat list of file resource IDs, which is later resolved into per-file relations by the `infer_relation_from_content` transformation.

```yaml
class_name: Dataset
description: "A Dataset class added back to the EMIM via add_class transformation"
id_property_name: accession
content_schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "additionalProperties": false,
    "description": "A Dataset.",
    "properties": {
      "id": { "type": "string" },
      "title": { "type": "string" },
      "description": { "type": "string" },
      "types": { "type": "array", "items": { "type": "string" } },
      "study_id": { "type": "string" },
      "dap": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "description": { "type": "string" },
          "text": { "type": "string" },
          "url": { "type": ["string", "null"], "format": "uri" },
          "duo_permission_id": { "type": "string" },
          "duo_modifier_ids": { "type": "array", "items": { "type": "string" } },
          "dac_id": { "type": "string" }
        },
        "required": ["id", "name", "description", "text", "duo_permission_id", "duo_modifier_ids", "dac_id"]
      },
      "dac": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "email": { "type": "string", "format": "email" },
          "institute": { "type": "string" }
        },
        "required": ["id", "name", "email", "institute"]
      },
      "files": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["id", "title", "description", "types", "study_id", "dap", "dac", "files"],
    "type": "object"
  }
relations:
  - relation_name: study
    description: "A relation from Dataset to Study."
    target_class: Study
    target_resource_id_field: study_id
    mandatory: MandatoryRelationSpec
    multiple: MultipleRelationSpec
```

### `infer_relation_from_content`

#### Dataset

Reconstructs the `dataset` relation on each EMIM file class by resolving the flat list of file IDs held on `Dataset.content.files`.

```yaml
source_class: Dataset
source_content_property: files
new_relation_name: dataset
description: "Reconstruct the dataset back-reference on each file class by resolving the flat list of file IDs held on Dataset.content.files."
target_classes:
  - ResearchDataFile
  - ProcessDataFile
  - IndividualSupportingFile
  - ExperimentMethodSupportingFile
  - AnalysisMethodSupportingFile
mandatory: # placeholder; defined during implementation
  origin: false
  target: false
multiple: # placeholder; defined during implementation
  origin: true
  target: false
```
