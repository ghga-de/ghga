# Global Unique IDs, Aggregate Transformations, and Workflow API (Mermaid's Purse)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope

### Outline

This epic delivers seven related improvements to the schemapack/metldata ecosystem and the em-transformation-service:

1. **Schemapack GUID support** — an opt-in `globallyUniqueIds` flag in the schemapack schema enforces globally unique resource IDs across all classes in validated datapacks.
2. **Metldata transformation additions** — `duplicate_class` is retained; the new `add_class` transformation is added to support the aggregate stats workflow.
3. **Metldata aggregate stats workflow** — the aggregate stats workflow is rewritten using the new GUID-compatible transformations.
4. **Metldata `WorkflowRunner` API** — `WorkflowHandler` is refactored to separate model derivation from data transformation. A new public `WorkflowRunner` class and a `validate_workflow` convenience function are added.
5. **GHGA metadata schema** (schemapack branch) — `Publication` is removed as a standalone class and embedded as inline content in `Study`.
6. **`jsonsubschema` fork** — `jsonsubschema` is forked under the GHGA organisation to ship a bug fix for enum values containing regex metacharacters.
7. **em-transformation-service updates** — the service adopts `WorkflowRunner` to replace its manual transformation loop.

### Terminology

`Global Unique ID (GUID)`: A resource identifier unique not just within a single class but across all classes in a schemapack schema. GHGA accessions are an example: every Study, Sample, Dataset, etc. receives a globally unique accession.

`Model Derivation`: Running a workflow's transformation steps on an input schema to produce the output schema.

`Data Transformation`: Running a workflow's transformation steps on a datapack to produce a transformed datapack.

`Transformation Registry`: A mapping from transformation names to their `TransformationDefinition` objects. It is the authoritative lookup table used when resolving workflow step names to executable transformations.

`WorkflowRunner`: The new high-level public class in metldata that executes a workflow. It accepts `workflow` and `input_model` at construction, eagerly derives the output schema (exposed via `.model`), and defers data transformation to `.run_workflow(data, annotation)` calls.

`Aggregate Stats Workflow`: A GHGA-specific metldata workflow that produces a representation of the GHGA ingress model optimised for aggregate statistics queries.

`Universal Discovery Model (UDM)`: The common target schema to which all EMIMs are transformed, serving as the basis for data queries and display in the GHGA Data Portal.

### Included/Required

#### 1. SchemaPack

##### 1.1. Globally Unique IDs Support

Schemapack shall support an opt-in `globallyUniqueIds` boolean flag at the schema level. When `true`, every resource ID across every class in a conforming datapack must be unique. The flag defaults to `false`, preserving backwards compatibility.

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
1. The schema does not have `globallyUniqueIds` set. The `duplicate_class` transformation works as it currently does, with no issues.
2. The schema has `globallyUniqueIds: true`. If a workflow duplicates a class and later deletes it, the final output contains no ID collision. Transient ID collisions introduced by `duplicate_class` within a workflow are permitted — the `globallyUniqueIds` constraint is enforced only on the final workflow output, not on intermediate steps.

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

> **Under discussion.** See the arguments below for an open question about whether `add_class` is necessary.

**Proposed design**

A new `add_class` transformation creates an empty class in the schema. It does not copy or duplicate any existing class. The new class has no resources initially; downstream transformation steps populate it.

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

Relations are declared at class-creation time when known upfront. Each key is the relation name (snake_case); the value specifies the target class and multiplicity/mandatory flags matching the schemapack relation definition format. All referenced target classes must already exist — `add_class` raises `ModelAssumptionError` if any are missing.

**Model transformation**

- Add the new `ClassDefinition` (with content schema and any declared relations) to the schemapack.
- Raise `ModelAssumptionError` if a class with `class_name` already exists.
- Raise `ModelAssumptionError` if any `target_class` in `relations` does not exist in the schema.

**Data transformation**

> **Open question:** How will the newly added class be populated with data?

**Arguments against `add_class`**

The need for `add_class` arises from a requirement to create classes in the derived schema with no direct counterpart in the input schema. However, populating such a class with data is not straightforward: it can only contain resources that already exist in the datapack. Given that, the required operation is essentially a copy-resource from an existing class — structurally similar to `duplicate_class`, but at the individual resource level rather than the class level. `duplicate_class` already handles the whole-class case, and content transformations cover schema changes.

What may be missing is explicit relation deletion. Currently, a duplicated class's relations are cleared only as a side effect of deleting other classes whose removal cascades to references. A `delete_relation` transformation would make this explicit, and may make `add_class` unnecessary.

##### 2.4. `WorkflowRunner` — Separated Model and Data Transformation

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

`WorkflowHandler` is restructured so that model derivation and data transformation become two distinct phases:

- **`__init__`**: walks the workflow once, builds a `WorkflowStepHandler` and derives the output schema for each step via `TransformationHandler`, and stores the `TransformationHandler` instances internally. The final output schema is exposed as an attribute.
- **`run()`**: iterates over the cached `TransformationHandler` instances, applies data transformations in order, and returns a `DataPack` directly. `WorkflowResult` (which previously bundled model and data) is removed.

Boundary validation is preserved: input schema/data is validated against the first step's assumptions; output schema/data is validated against the last step's output model.

On top of `WorkflowHandler`, a new public `WorkflowRunner` class is introduced in `src/metldata/workflow/run.py`. It is registry-aware and accepts `workflow` and `input_model` as keyword arguments at construction. Model derivation happens eagerly in `WorkflowRunner.__init__`; the schema is exposed via the read-only `.model` property. Data transformation is deferred: callers invoke `.run_workflow(data=..., annotation=...)` once per datapack. This allows consumers to pay the schema-derivation cost once at construction and call `.run_workflow()` repeatedly without managing `TransformationHandler`, the registry, or intermediate schema state directly.

A convenience function `validate_workflow()` is added to `src/metldata/workflow/validate.py`; it delegates to `validate_workflow_against_registry` using the built-in registry so callers do not need to pass a registry explicitly.

###### Public API Surface

The following are the stable public exports from `metldata.__init__`:

| Name                | Kind     | Purpose                                                     |
| ------------------- | -------- | ----------------------------------------------------------- |
| `WorkflowRunner`    | class    | High-level workflow execution; `.model` + `.run_workflow()` |
| `validate_workflow` | function | Validates a workflow against the built-in registry          |



##### 2.5. Aggregate Stats Workflow Integration Test

An end-to-end integration test shall be added to metldata exercising all new capabilities together: a `globallyUniqueIds` schema, `add_class` (pending resolution of section 2.3), correct error behaviour for `duplicate_class` when intermediate validation is enabled, and `WorkflowRunner` running model derivation and data transformation independently.

The test uses a representative aggregate stats workflow and verifies that the `globallyUniqueIds` constraint is enforced on the output: validation rejects datapacks with duplicate IDs across classes.


##### 2.6. Performance Benchmark of the Aggregate Stats Workflow

A performance benchmark shall be run against the full EMIM → aggregate stats workflow using the Epignostix dataset as a representative input. Profiling is done via `cProfile`. The goal is to establish a baseline transformation time before production deployment. Results are attached to the epic. Any step that accounts for a disproportionate share of total time is flagged for investigation.



#### 3. GHGA Metadata Schema (schemapack branch)

##### 3.1. Publication as Study Content

In the LinkML-based GHGA metadata schema, `Publication` is a first-class entity with a `study` relation back to `Study`. In the schemapack-based revision, this design changes: **`Publication` is no longer a separate class**. Publication data is embedded directly in `Study` content as an inline array of publication objects.

The `Study` content schema shall include a `publications` property: an array of objects with relevant fields (e.g., `doi`, `title`, `abstract`, `author`, `year`, `journal`, `xref`). There is no `Publication` class and no `study` relation on a publication resource.

##### 3.2. Updating Schema Dependencies

Embedding `Publication` in `Study` requires updates to the `ghga-transpiler` library and the `generate_xlsx.py` script in the metadata-schema schemapack branch. Both must be updated to reflect the new schema structure.


#### 4. em-transformation-service: Adopt `WorkflowRunner`

The em-transformation-service currently drives workflow execution by manually iterating over transformation steps and managing `TransformationHandler` instances. This must be replaced with `WorkflowRunner`.

**Model derivation** (`model_derivation.py`): replace the manual step loop with `WorkflowRunner(workflow=..., input_model=input_schema)` and read `runner.model`.

**Data transformation** (`aem_pack_registry._apply_workflow_to_data`): replace the manual step loop with `runner.run_workflow(data=data, annotation=annotation)`.

After the change, the service no longer imports `TransformationHandler`, manages intermediate schema state, or resolves transformation names from the registry directly. A `WorkflowRunner` instance is constructed once per route at config-validation time and reused for all data transformations on that route.


#### 5. `jsonsubschema` Enum Bug Fix

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

1. A workflow author designing the EMIM → UDM workflow needs a derived class with no direct counterpart in the EMIM, constructed from content spread across existing classes.
2. The author adds an `add_class` step specifying the class name, `id_property_name`, and the content JSON Schema.
3. Subsequent steps (e.g., `transform_content`) populate the new class from existing class resources.
4. The workflow validates with `validate_workflow(workflow)` without errors.
5. `WorkflowRunner(workflow=workflow, input_model=emim_schema).model` produces the UDM schema with the new class present.

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


### Optional

- A `copy_class` transformation: creates a new class as a structural copy of an existing class but assigns fresh resource IDs rather than duplicating them.

### Not Included

- An `add_relation` or `delete_relation` transformation — not required for the current aggregate workflow.
- `jsonsubschema` upgrade to support JSON Schema draft 2019-09 or later.


## Human Resource/Time Estimation

Number of sprints required: 3

Number of developers required: 2
