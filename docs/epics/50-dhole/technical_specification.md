# Rewriting existing metldata transformations (Dhole)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
The aim is to rewrite all existing metldata transformations to use schemapack.


### Included/Required:
- add possibility to use custom embedding profile to configure the denormalization
  in schemapack
- migrating the already schemapack-based transformations to spec version 0.2.0
  (see https://github.com/ghga-de/metldata/tree/poc/src/metldata/schemapack_/builtin_transformations):
  - delete_properties
  - infer_relations
- re-implement the following LinkML-based transformations to use schemapack
  (see https://github.com/ghga-de/metldata/tree/poc/src/metldata/builtin_transformations):
  - merge_slots
- re-evaluate and potentially refactor the following transformations:
  - aggregate


### Not included:
- Reimplementation of the custom_ebeddings transformation is not required since it will already
  covered by builtin functionality of schemapack
- Reimplementation of the add_accessions transformation is postponed since it might be
  moved handled by the submission store and not be implemented as transformation.
- A full reimplementation of the GHGA transformation workflow (this depends on other changes to
  be in place first and would make this epic dependent on other lines of work).
- The normalize_model transformation is not needed anymore

## Additional Details:

### Embedding Profile to Configure Denormalization:

This helps to control which relations (and relations of relations) will be embedded and
which won't. It can even be used to deal with circular dependencies that would otherwise
lead to an exception when denomalizing.

Here is an example:

Given the following rooted schemapack:
```yaml
schemapack: 0.2.0
description: A schema used to describe relationships between team members.
classes:
  Person:
    id:
      propertyName: name
    content: ../../content_schemas/AnyObject.schema.json` # Any object allowed
    relations:
      teammates:
        targetClass: Person # refering to itself
        mandatory:
          origin: false
          target: false
        multiple:
          origin: true
          target: true
      manager:
        targetClass: Person # refering to itself
        mandatory:
          origin: false
          target: false
        multiple:
          origin: true
          target: false

  rootClass: Person
```

There is the following datapack:
```yaml
datapack: 0.2.0
resources:
    Person:
        Alice:
            content: {}
            relations:
                teammates:
                    - Bob
                    - Charlie
                manager: Dave
        Bob:
            content: {}
            relations:
                teammates:
                    - Alice
                    - Charlie
                manager: Dave
        Charlie:
            content: {}
            relations:
                teammates:
                    - Alice
                    - Bob
                manager: Dave
        Dave:
            content: {}
            relations:
                teammates: []
                manager: Eve
        Eve: # the boss of Dave
            content: {}
            relations:
                teammates: []
                manager: null
rootResource: Alice
```

Running a denormalization without configuration would not work because there are
circular dependencies between Alice, Bob, and Charlie regarding the teammates relation.

To resolve that, the following embedding profile can be used to configure the
denormalization process:

```yaml
teammates:
  # do embed teammates, however, for each embedded teammate the following embedding
  # restrictions apply:
  teammates: false # do not embed teammates of teammates
  manager: false # do not embed managers of teammates
manager: true # do embed the managers and all the nested relations that the manager
              # might have
```

The outcome would be the following denormalized data:
```yaml
name: Alice
teammates:
  - name: Bob
    teammates:
      - Alice
      - Charlie
    manager:
      - Dave
  - name: Charlie
    teammates:
      - Alice
      - Bob
    manager:
      - Dave
manager:
  name: Dave
  teammates: []
  manager:
    name: Eve
    teammates: []
    manager: null
```

### Immutability of Datapack and Schemapack Objects:
Currently, the pydantic models for interacting with DataPack and SchemaPack
definitions are not fully frozen, yet, however in the future they will be.
Thus, while re-implementing the transformations, modifications to a
DataPack or SchemaPack object should never be done in place but
using methods that would also work on frozen pydantic models (e.g.
the `model_copy(update={...})` method). This is also true for the already
migrated transformation.

### Refactor merge_slots transformation:
The original merge_slots transformation should be replaced by two new transformations:

A. For merging content properties:
- nested properties (of nested JSON objects) must be supported
- If the source properties are not of the same type and the `assume_same_type` argument
  (see config example below) is set to `false`, a union type is created (AnyOf).
- The new property is always a list even if the source properties were not multivalued.
- a config example might look like this:
  ```yaml
  merge_content_properties:
    ClassA:
      # merged properties that shall be created in ClassA:
      new_property_x:
        source_properties:
          - old_property_a
          - old_property_b
        deduplicate: true # the default, all values are kept even if they occur
                          # multiple times accross the source properties
        assume_same_type: true # the default, raises an exception if the source
                               # properties do not have the same type
      old_property_c.new_property_y:
        # support for nesting:
        # A new property shall be created in the object contained in the
        # `old_property_c`. The properties `nested_property_d" and `nested_property_e`
        # inside of the object contained in `old_property_c` serve as sources.
        # Dots ('.') are used to denote nesting. If a property name contains a dot, it
        # can be escaped using '\.'. We assume that nobody would have `\.` in their
        # property names, so that cannot be escaped.
        source_properties:
          - old_property_c.nested_property_d
          - old_property_c.nested_property_e
        deduplicate: true
        assume_same_type: false # Will create a union type if the source properties
                                # differ in type.
    ClassB:
      # merged properties for ClassB:
      new_property_z:
        source_properties:
          - old_property_a
          - old_property_b
        # not specifying `deduplicate` and `assume_same_type` is equivalent to
        # their defaults
  ```

B. For merging relation properties:
- the source properties must have the same targetClass
- a config example might look like this:
```yaml
  merge_relation_properties:
    ClassA:
      # merged relation properties that shall be created in ClassA:
      new_property_x:
        source_properties:
          - old_property_a
          - old_property_b
        # There are no option `deduplicate` because relation properties may never
        # contain duplicate values.
        # Moreover, there is no option `assume_same_type` since currently schemapack
        # does not support unions of multiple target classes for a relation. Thus
        # the source relations must all point to the same target class.
        # Nesting is also not supported in relations, so not special treatment of
        # dots is required.
      new_property_y:
        # another merged property
        source_properties:
          - old_property_a
          - old_property_b
    ClassB:
      # merged properties for ClassB:
      new_property_z:
        source_properties:
          - old_property_a
          - old_property_b
  ```

### Refactor aggregate transformation:

The former `aggregate` transformation shall be replaced by a mixture of existing
and to be written transformations. The following new transformations shall be
implemented:

#### Transformation 1: Add Content Property

A transformation that enables the insertion of a subschema into a new property
of any object within the current content schema of a class, including an initial
value. The schema will be modified by inserting the subschema at the specified path. The data will be modified by inserting the default value at the specified path. The user may control whether or not the newly added property is added to the parent property's `required` list.

##### Configuration

```yaml
# Generic Example, defaults shown for optional parameters
- class_name: MyClass
  target_content:
    object_path: "" # Optional, default empty string refers to content root object
    property_name: new_property
    required: true # Optional
  schema: # Optional, defaults to the following value
    type: "object"
    additionalProperties: false
  value: {} # Optional

# Examples from current config
- class_name: Dataset
  target_content:
    property_name: datasets

- class_name: Dataset
  target_content:
    property_name: "studies_summary"
```

#### Transformation 2: Count References

> [!IMPORTANT]  
> The following transformations are expected to add a new property to the schema and data as specified under `target_content`. They shall validate that the path specified under `object_path` is valid, i.e. leads to a property of type `"object"` and that that object does not yet contain a property by the name specified under `property_name`. They shall then add that property with an appropriate subschema as required by the specific transformation.

* The transformation shall count how many target objects are referenced from each source object given the relation name.
* The transformation shall validate whether the target is defined with multiplicity and fail otherwise

Example config:

```yaml
- class_name: Dataset
  target_content:
    object_path: samples_summary
    property_name: count
  source_relation_path: "Dataset(samples)>Sample"
```

####  Transformation 3: Count content values

* The transformation shall count the values encountered at a specified property in the content of an object.
* The transformation shall validate that at least one of the traversed references is multi-valued by its cardinality or one of the traversed content elements is an array.
* The path to the source content property is specified in two stages: (1) a relation path string specifies the path to the class that holds the content; (2) a content path specifies the path to the property source property within the content.
* A new content property with the name `target_content.property_name` will be added to the schema by the transformation and will have the following schema
  ```yaml
  type: object
  additionalProperties: true
  ```
  where each observed value will be mapped to an integer value representing the
  number of times it was observed

##### Configuration

```yaml
- class_name: Dataset
  target_content:
    object_path: samples_summary.stats
    property_name: sex
  source:
    relation_path: Dataset(individuals)>Individual
    content_path: some.nested.properties.sex # Can contain dot notation for nested objects
- class_name: Dataset
  target_content:
    object_path: samples_summary.stats
    property_name: tissues
  source:
    relation_path: Dataset(biospecimens)>Biospecimen
    content_path: tissue
```

#### Transformation 4: Sum Operation

* Similarly to the previous transformation, this transformation does not count the element occurrences but sums up the values of the yielded elements.
* The transformation shall validate that the type of the configured source element allows arithmetic operations (number, integer, boolean).

Draft Config:

```yaml
- class_name: Dataset
  target_content:
    object_path: files_summary.stats
    property_name: size
  source:
    relation_path: Dataset(files)>File
    content_path: size
```

#### Transformation 5: Copy

* The transformation shall enable copying the values from one content location (of potentially a referenced class) to another content location.
* The type of the resulting subschema shall be that of the source subschema.

##### Configuration

```yaml
- class_name: Dataset
  target_content:
    property_name: dac_email
  source:
    relation_path: Dataset(data_access_policy)>DataAccessPolicy(data_access_committee)>DataAccessCommittee
    content_path: email
```

#### Transformation 6: Delete Relation

Deletes a relation from the model and data.

##### Configuration

```yaml
- class_name: ClassName
  relation_name: reference_name
```

#### Transformation 7: Delete Content Subschema

As the name suggests, following the conventions used in the aforementioned transformations. The transformation changes the schema and data by removing the specified property from the content schema and data.

```yaml
- class_name: ClassName
  content_path: property.nested_property
```

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: multiple
