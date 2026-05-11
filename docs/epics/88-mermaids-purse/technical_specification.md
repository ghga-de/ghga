# Global Unique IDs, Aggregate Transformations, and Workflow API (Mermaid's Purse)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope

### Outline

This epic delivers four related improvements to the schemapack/metldata ecosystem and the em-transformation-service:

1. **Schemapack GUID support** — an opt-in `global_unique_ids` flag in the schemapack schema enforces globally unique resource IDs across all classes in validated datapacks. 
2. **Metldata transformation additions** — the `duplicate_class` transformation is retained but updated to raise an error when the input schema enforces globally unique IDs, since duplicating a class would produce ID collisions; the new `add_class` transformation is added to support building aggregate stats transformation workflow.
3. **Metldata implement aggregate stats workflow** - aggregate stats workflow is rewritten using the new GUID-compatible transformations.
4. **Metldata workflow runner API** — the internal `TransformationHandler` loop is encapsulated behind a clean `WorkflowRunner` public class that separates model derivation from data transformation, eliminating the API leakage that currently forces third-party services to manage low-level transformation details.
5. Changes to the **GHGA metadata schema** (schemapack branch) to reflect the new design where `Publication` is not a separate class but embedded in `Study` content.
6. Forking and releasing jsonsubschema with a bug fix to support enum values with regex metacharacters, which currently causes incorrect validation results against the GHGA metadata schema.
7. **em-transformation-service updates** — the service adopts `WorkflowRunner` to replace its manual transformation loop.

### Terminology

`Global Unique ID (GUID)`: A resource identifier that is unique not just within a single class but across all classes in a schemapack schema. GHGA accessions are an example: every Study, Sample, Dataset, etc. receives a globally unique accession.

`Model Derivation`: Running a workflow's transformation steps on an input schema to compute the output schema. 

`Data Transformation`: Running a workflow's transformation steps on a datapack to produce a transformed datapack.

`Transformation Registry`: A mapping from transformation names to their `TransformationDefinition` objects. It is the authoritative lookup table used when resolving workflow step names to executable transformations.

`WorkflowRunner`: The new high-level public class in metldata that executes a workflow. It exposes `transform_model` and `transform_data` as independent operations, hiding the internal `TransformationHandler` loop.

`Aggregate Stats Workflow`: A GHGA-specific metldata workflow that produces another representation of the GHGA ingress model that is optimised for aggregate statistics queries. 

`Universal Discovery Model (UDM)`: The common target schema to which all EMIMs are transformed, serving as the basis for data queries and data display in the GHGA Data Portal.

### Included/Required

#### 1. SchemaPack

##### 1.1. Global Unique ID Support

Schemapack shall support an opt-in `global_unique_ids` boolean flag at the schema level. When `true`, every resource ID across every class in a conforming datapack must be unique.

**Schema definition**

```yaml
schemapack: 5.0.0
global_unique_ids: true   # opt-in; default false
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

The flag defaults to `false`, preserving backwards compatibility with all existing schemapacks and datapacks.

**Datapack validation**

When validating a datapack against a schema with `global_unique_ids: true`:

1. Build a dict `{resource_id: [class_name, ...]}` by iterating over every class and appending the class name to the list for each of its resource IDs.
2. Filter the dict for entries whose list has more than one element — these are the collisions.
3. For each collision, raise a validation error that names the conflicting resource ID and every class in which it appears.

##### 1.2. Serialization fix (frozen dicts / circular reference)

Schemapack's serialization of `DataPack` objects (which use frozen dicts internally) currently triggers `ValueError: Circular reference detected (id repeated)` in naive client code. The fix shall be applied inside schemapack so that client code requires no workarounds.

#### 2. Metldata 

##### 2.1 `duplicate_class` Compatibility with Global Unique IDs

This section does not include any changes to `duplicate_class` itself, which continues to function as it currently does. It only clarifies how the presence of `global_unique_ids` in the schema affects the validation of workflow outputs that use `duplicate_class`.

The `duplicate_class` transformation shall be retained in the transformation registry; the `global_unique_ids` constraint does not conflict with its presence. There are two scenarios to consider:
1. The schema does not have `global_unique_ids` set. The `duplicate_class` transformation works as it currently does, with no issues.
2. The schema has `global_unique_ids: true`. If a workflow duplicates a class and later deletes it, the final output contains no ID collision. Transient ID collisions introduced by `duplicate_class` within a workflow are permitted — the `global_unique_ids` constraint is enforced only on the final workflow output, not on intermediate steps.

The second scenario is consistent with the existing metldata behaviour: when the no-intermediate-validation flag is set, model compatibility is not enforced after every step — only at the workflow boundaries. The `global_unique_ids` uniqueness constraint follows the same rule: it is enforced only at **workflow output validation** (the final step), not during intermediate steps. If the output schema of a workflow still has `global_unique_ids: true` and the output datapack contains duplicate IDs across classes, the post-workflow validation raises an error at that point.

##### 2.2. `add_class` Transformation

A new `add_class` transformation creates an empty class in the schema. It does not copy or duplicate any existing class. The new class has no resources in the datapack initially; downstream transformation steps are responsible for populating it.

**Configuration model**

```python
class RelationDefinition(BaseModel):
    target_class: str
    mandatory_origin: bool = False
    mandatory_target: bool = False
    multiple_origin: bool = False
    multiple_target: bool = False
    description: str | None = None

class AddClassConfig(BaseModel):
    class_name: str                                    # PascalCase; must not already exist in the schema
    id_property_name: str                              # the property used as the resource ID
    content_schema: dict                               # a valid JSON Schema object for the class content
    relations: dict[str, RelationDefinition] = Field(default_factory=dict)
    description: str | None = None
```

Relations are declared at class-creation time when they are known upfront. Each key is the relation name (snake_case); the value specifies the target class and multiplicity/mandatory flags matching the schemapack relation definition format. All referenced target classes must already exist in the schema — `add_class` raises `ModelAssumptionError` if any target class is missing.

**Open question:** How will the newly added class and its relations be populated?


**Model transformation**

- Add the new `ClassDefinition` (with content schema and any declared relations) to the schemapack.
- Raise `ModelAssumptionError` if a class with `class_name` already exists.
- Raise `ModelAssumptionError` if any `target_class` in `relations` does not exist in the schema.

**Data transformation**

How will we populate the data for the newly added class? 

##### 2.3. `WorkflowRunner` — Separated Model and Data Transformation

**Problem**

Third-party services that use metldata to run transformation workflows (e.g., em-transformation-service) currently interact with `TransformationHandler` directly:

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

This couples model derivation and data transformation into one loop. The em-transformation-service needs them separate: it derives all output schemas once at startup, then transforms datapacks individually at runtime. The existing `WorkflowHandler.run()` does not support this split either.

**Solution: `WorkflowRunner`**

```python
class WorkflowRunner:
    def __init__(
        self,
        workflow: Workflow,
        transformation_registry: TransformationRegistry | None = None,
    ) -> None:
        """
        Uses the default built-in registry when transformation_registry is None.
        Validates the workflow against the registry at construction time.
        """
        ...

    def transform_model(self, input_schema: SchemaPack) -> SchemaPack:
        """
        Run the model-transformation phase of every workflow step in order.
        Validates the input schema before the first step and the output schema
        after the last step. Returns the final transformed schema.
        """
        ...

    def transform_data(
        self,
        data: DataPack,
        input_schema: SchemaPack,
        annotation: SubmissionAnnotation,
    ) -> DataPack:
        """
        Run the data-transformation phase of every workflow step in order.
        Derives the intermediate schemas internally (equivalent to transform_model
        applied step-by-step) — callers do not manage schema state.
        Validates the input data before the first step and the output data
        after the last step. Returns the final transformed datapack.
        """
        ...
```

The intended usage in a third-party service becomes:

```python
# At config/startup time (model derivation)
runner = WorkflowRunner(workflow=my_workflow)
output_schema = runner.transform_model(input_schema)

# At runtime (data transformation, per incoming datapack)
output_data = runner.transform_data(data, input_schema, annotation)
```

##### Public API surface for metldata

The following are the stable public exports:

| Name                          | Kind     | Purpose                                                      |
| ----------------------------- | -------- | ------------------------------------------------------------ |
| `WorkflowRunner`              | class    | High-level workflow execution (this epic)                    |
| `get_transformation_registry` | function | Returns the default registry                                 |
| `validate_workflow`           | function | Validates a workflow against a registry without executing it |

`validate_workflow` signature:

```python
def validate_workflow(
    workflow: Workflow,
    transformation_registry: TransformationRegistry | None = None,
) -> None:
    """
    Raises WorkflowValidationError if any step name is not in the registry
    or if step configurations are invalid. Uses the default registry when
    transformation_registry is None.
    """
    ...
```

`WorkflowRunner` shall be importable from `metldata.workflow.runner`. The existing `WorkflowHandler` and `TransformationHandler` remain available internally but are not part of the public API.



##### 2.4. Aggregate Stats Workflow Integration Test

An end-to-end integration test shall be added to metldata that exercises all the new capabilities introduced in this epic together: a `global_unique_ids` input schema, `add_class`, `duplicate_class` failing correctly on such a schema, and `WorkflowRunner` running model derivation and data transformation separately.

The test uses a representative aggregate stats workflow and verifies `global_unique_ids: true` The input schemapack has the flag set; validation correctly rejects datapacks with duplicate IDs across classes.


##### 2.5. Performance Benchmark of the Aggregate Stats Workflow

A performance benchmark shall be run against the full EMIM → aggregate stats workflow using the Epignostix dataset as a representative real-world input. The benchmark will be done via cProfile library. The goal is to establish a baseline transformation time before the workflow is deployed to production.

Results are recorded and attached to the epic. They inform whether any transformation steps are unexpectedly slow and whether further optimisation is needed before shipping. If any single step accounts for a disproportionate share of the total time, it is flagged for investigation.



#### 3. GHGA Metadata Schema (schemapack branch)

##### 3.1. Publication as Study Content

In the LinkML-based GHGA metadata schema, `Publication` is a first-class entity with its own class and a `study` relation pointing back to `Study`. In the schemapack-based revision of the GHGA metadata schema, this design is changed: **`Publication` is not modelled as a separate class**. Instead, publication data is embedded directly in the `Study` content schema as an inline array of publication objects.

The `Study` content schema shall include a `publications` property containing an array of objects with the relevant publication fields (e.g., `doi`, `title`, `abstract`, `author`, `year`, `journal`, `xref`). There is no `Publication` class and no `study` relation on a publication resource.

##### 3.2. Updating schema dependencies based on the change

Moving the Publication class under Study content has implications for the ghga-transpiler library and the metadata-schema schemapack branch's generate_xlsx.py script. Both need to be updated to reflect the new schema structure.


#### 4. em-transformation-service: Adopt `WorkflowRunner`

The em-transformation-service currently drives workflow execution by manually iterating over transformation steps and managing `TransformationHandler` instances directly. This must be replaced with `WorkflowRunner` once it is available.

**Model derivation** (`model_derivation.py`): replace the manual step loop that builds the output schema with a call to `runner.transform_model(input_schema)`.

**Data transformation** (`aem_pack_registry._apply_workflow_to_data`): replace the manual step loop that transforms each datapack with a call to `runner.transform_data(data, input_schema, annotation)`.

After the change, the service no longer imports `TransformationHandler`, manages intermediate schema state, or resolves transformation names from the registry directly. A `WorkflowRunner` instance is constructed once per route at config-validation time and reused for every data transformation on that route.


#### 5. `jsonsubschema` Enum Bug Fix

Metldata depends on the `jsonsubschema` library (IBM) for JSON Schema subset validation. The library is not actively maintained and contains a known bug: in `_canonicalization.py`, enum values are converted to regex patterns using bare string concatenation (`"^" + str(x) + "$"`) without escaping regex metacharacters. Any enum value containing a special character such as `^`, `*`, `+`, or `.` is therefore misinterpreted as a regex operator, causing incorrect validation results.

This bug manifested against the GHGA `instrument_model` controlled vocabulary: the enum value `454_GS_FLX+` contains a `+` character. Without escaping, the generated pattern becomes `^454_GS_FLX+$`, which matches strings like `454_GS_FLXXX` rather than the literal value `454_GS_FLX+`, causing incorrect schema subset validation. The upstream fix is captured in [IBM/jsonsubschema@8e6535](https://github.com/IBM/jsonsubschema/commit/8e6535461d00f37e4c06189826d320e4750d3a31).

The upstream maintainers are unresponsive, so the fix cannot be obtained via a normal upstream release. The solution is to **fork `jsonsubschema` under the GHGA organisation**, and publish a GHGA-maintained release to PyPI (or the internal package registry). Metldata's dependency then points to the GHGA fork instead of the IBM original.

Concretely:

1. Fork `IBM/jsonsubschema` to `ghga-de/jsonsubschema`.
2. Apply the fix from [IBM/jsonsubschema@8e6535](https://github.com/IBM/jsonsubschema/commit/8e6535461d00f37e4c06189826d320e4750d3a31) on the fork.
3. Tag and publish a release from the fork.
4. Update metldata's dependency to reference the GHGA fork release.
5. Identify the specific GHGA CV value that triggers the bug and add a regression test to metldata that fails without the fix and passes with it.


**Another issue with the library.** The library only supports JSON Schema draft 4. The GHGA metadata schema declares `$schema: https://json-schema.org/draft/2019-09/schema`. Keywords introduced after draft 4 (e.g., `$defs`, `unevaluatedProperties`) are silently ignored or mishandled, making subset validation unreliable for schemas that use draft 2019-09 features. We will not tackle this in the scope of this epic. But it is something to consider for the future usage of that library. 

## User Journeys

### Journey 1: Schema Designer Enables Global Unique IDs


1. A schema designer adds `global_unique_ids: true` to the schema YAML.
2. When they run `schemapack validate` against a conforming datapack, validation succeeds only if all resource IDs are distinct across all classes.
3. If a collision is present — e.g., the Study `GHGAS00001` and a Sample also named `GHGAS00001` — validation fails with a clear error naming the conflicting ID and the two classes that claim it.

### Journey 2: Workflow Author Builds an Aggregate Stats Workflow with `add_class`

1. A transformation workflow author is designing the EMIM → UDM workflow.
2. The UDM requires a derived class that has no direct counterpart in the EMIM and must be constructed from content spread across existing EMIM classes.
3. The author adds an `add_class` step at the appropriate point in the workflow, specifying the class name, `id_property_name`, and the JSON Schema for the class content.
4. Subsequent workflow steps (using `transform_content` or similar) populate the new class resources by extracting or deriving content from existing classes.
5. The workflow is validated with `validate_workflow(workflow)` without errors.
6. Running `WorkflowRunner(workflow).transform_model(emim_schema)` produces the UDM schema with the new class correctly present.

### Journey 3: em-transformation-service Derives Models and Transforms Data Independently

1. The em-transformation-service starts up and loads its transformation configuration.
2. For each route, it instantiates a `WorkflowRunner` and calls `runner.transform_model(input_schema)` to derive the output schema. No datapacks are required at this stage.
3. The derived output schema is stored alongside the route and used to validate incoming data.
4. When an AnnotatedEMPack arrives at runtime, the service calls `runner.transform_data(data, input_schema, annotation)` to produce the derived datapack. The service does not manage `TransformationHandler` instances or intermediate schema state.
5. The resulting datapack is validated against the pre-derived output schema and published.

## Additional Implementation Details

- The `global_unique_ids` flag defaults to `false`. No existing schemapack file or datapack needs to be modified.
- `WorkflowRunner.transform_data` must internally re-derive the intermediate schemas at each step — it cannot assume that `transform_model` has been called first. This keeps the two methods fully independent.
- The validation that currently occurs at both ends of `WorkflowHandler.run()` must be preserved in `WorkflowRunner`: input schema/data validated against the first step's assumptions; output schema/data validated against the last step's output model.
- `WorkflowRunner` embeds the transformation registry so callers do not need to import or manage it, unless they need a custom registry (e.g., for testing).
- The serialization fix for frozen dicts should be shipped as a patch release of schemapack before or alongside the main changes in this epic.


### Optional

- A `copy_class` transformation: creates a new class as a structural copy of an existing class, but assigns fresh resource IDs rather than duplicating them. Useful when the logical structure of a class is reused in a derived model.

### Not included

- A `add_relation` or `delete_relation` transformation — not required for the current aggregate workflow. (or is it?)
- jsonsubschema library upgrade to a version that supports JSON Schema draft 2019-09 or later. 


## Human Resource/Time Estimation

Number of sprints required: 3

Number of developers required: 2
