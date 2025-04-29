# Metldata Transformation Finalzation (Common Furniture Beetle)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).


## Scope

### Outline:

The goal of this epic is to implement and refactor transformations to transition to schemapack and a new workflow language in metldata.

### Included / Required:

The following additional transformations shall be implemented or refactored in metldata.

#### Duplicate Class

This transformation shall duplicate a class and all its corresponding objects.

```yaml
source_class_name: SomeClass # Must exist
target_class_name: SomeOtherClass # Must NOT exist
```

ID, relations and content will be identical in the new class. All object will be duplicated.

#### Delete Class

This transformation shall delete a class from the schema. All objects of this class type in the data shall also be removed, including all references in all classes that are of the type of the deleted class.

Example Config:

```yaml
class_name: ClassNameToDelete
```

#### Transform Content

The transform content transformation shall enable the universal modification of content schemas and content data based on the current state. The schema transformation shall be expressed in form of a new schema spec. The data transformation shall be expressed in form of a Jinja template using the current data in form of a denormalized object named `original` with an arbitrary embedding profile.

Example config:

```yaml
class_name: SomeClass
schema: {} # Some JSON schema
embedding_profile: {} # Some embedding profile for denormalization
data_template: | # The Jinja Template for the new data
  title: "{{ original.title }}"
  dac_email: "{{ original.data_access_policy.data_access_committee.email }}"
  description: "{{ original.description }}"
  sex_dist: 
    {% for sex, matches in original.individuals | groupby("sex") %}
      value: "{{ sex }}" 
      count: {{ matches | length }}
    {% endfor %}
```

#### Refactoring of existing transformations

Given the new workflow specification concept outlined in the [Carpenter Bee Epic Spec](../55-carpenter-bee/technical_specification.md) existing transformations shall be refactored such that they only perform one unit of action at a time. For example, the `infer_references` transformation shall be configured as follows:

```yaml
class_name: SomeClass
relation_name: some_new_relation
relation_path: "SomeClass(some_relation)>OtherClass"
```

The transformations implemented as a part of Dhole epic `count_content_values`, `count_references`, `sum_operation`, `delete_content_subschema`, `copy_content` and `add_content_properties` will be replaced by the `transform_content` transformation. Thus, they will not be subject to refactoring.

Any existing content schema transformation involving a passive path element will be represented with two transformations; one for resolving the the path and adding the relation (with `infer_relations`), the other one transforming the content (with `transform_content`). If not needed, the temporary relation may be deleted in subsequent workflow steps.

## Human Resource/Time Estimation:

Number of sprints required: ?

Number of developers required: ?
