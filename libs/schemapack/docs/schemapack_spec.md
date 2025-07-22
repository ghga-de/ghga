# Schemapack Specification

This document describes the structure and components of a `schemapack.yaml` file, which defines the schema used to validate and interpret datapacks. Each schemapack includes:

* A schemapack version identifier

* An optional schema description

* A classes section, where each class represents a distinct entity type with associated content and its relations. Classes define the internal structure (content) of their instances using JSON Schema and may specify relationships (relations) to other classes defining constraints on how instances of different classes are linked, including their multiplicity and participation.

### Keywords:

`schemapack`: Specifies the Schemapack version the schema is built under.

`description` *(optional)*: A short, human-readable summary of the schema.

`classes`: A mapping of class names to *class definitions*. Class names must use PascalCase.

Example:
```yaml

schemapack: 3.0.0
description: Schema for experimental metadata
classes:
    Experiment:
        ...
```

`rootClass` *(optional)*: Defines the name of a class that should acting as the root of the schemapack.

> [!IMPORTANT] A rooted schemapack requires its corresponding datapack to be rooted as well. If you're validating a rooted datapack agains a schema, make sure that its schemapack counterpart is also rooted. If not specified , i.e. set to None (the default), the datapack must not specify a root resource.


#### Class Definition

A class definition includes the following properties:

`description` *(optional)*: A brief explanation of the class.

`id`: Defines the class's identifier property. Must follow this structure:

* `propertyName`: The name of the identifier property. Must not conflict with names used in `content` or `relations`.

* `description` *(optional)*: A human-readable description of the identifier.

    Example:
    ```yaml

    id:
        propertyName: alias
        description: alias is id
    ```

`content`: A schema describing the structure of the class content. Must be a valid JSON Schema object. You may embed it inline or reference an external JSON or YAML file, which will be automatically loaded.

```yaml

content: content_schemas/Experiment.schema.json # <- path to the json schema
```

``` yaml
content: # <- content schema embedded here
    type: object
    properties:
        name:
            type: string
        description:
            type: string
```


Given that the content of the Experiment.schema.json file is:
```json
{
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "description": {
            "type": "string"
        }
    }
}
```

`relations` *(optional)*: A mapping of relation names to *relation definitions*. Relation names must:
  * Use `snake_case`.
  * Start with a letter.
  * Contain only alphanumeric characters and underscores.
  * Must not conflict with property names used in `content`

Example:

```yaml

schemapack: 3.0.0
description: Schema for experimental metadata
classes:
    Experiment:
        id:
            propertyName: alias
            description: alias is id
        content: content_schemas/Experiment.schema.json
        relations:
            samples: # <- relation name
                ...
```


#### Relation Definition

Each relation defines how a class relates to another class. Relation definition include the following properties:

`description` **(optional)**: A short description of the relation.

`targetClass`: The name of the class being referenced.

`mandatory`: Describes the minimum number of instances required from the origin and target side. `origin` is true if every target must have at least one instance from the origin side, and `target` is true if every origin must have at least one instance from the target side.

Example:
```yaml

mandatory:
    origin: true
    target: true
```

`multiple`: Describes the maximum number of instances allowed from from the origin and target side. `origin` is true if the target may have multiple instances from the origin side, and `target` is true if the origin may have multiple instances from the target side.

Example (for a many-to-one relation):
```yaml

multiple:
    origin: true
    target: false
```


A full schemapack example:

```yaml

schemapack: 3.0.0
description: Schema for experimental metadata
classes:
    Experiment:
        id:
            propertyName: alias
            description: alias is id
        content: content_schemas/Experiment.schema.json
        relations:
            samples:
                targetClass: Sample
                mandatory:
                    origin: true
                    target: true
                multiple:
                    origin: true
                    target: false
    Sample:
        id:
            propertyName: alias
            description: alias is id
        content: content_schemas/Sample.schema.json
```
This schema defines two classes, Experiment and Sample, and a relation between them. The content schemas are loaded from external JSON files.
