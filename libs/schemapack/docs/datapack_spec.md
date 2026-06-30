# Datapack Specification

This document defines the structure and required fields of a `datapack.yaml` file, which represents structured data conforming to a given schemapack. Each datapack consists of:

* A datapack version identifier,

* A resources section containing all data instances grouped by class and uniquely identified, following a format with clearly separated content (data fields) and relations (links to other resources),

* Optional rootResource and rootClass fields to restrict the datapack to a subgraph of interest.


### Keywords:

`datapack`:  Specifies the version of the datapack specification being used.

Example:
```yaml

datapack: 3.0.0
```

`resources`:A nested dictionary containing resources per class name and resource ID. Each class defined in the schemapack must be present even if no resources are defined for it in this datapack.


Example:
```yaml

datapack: 3.0.0
resources:
    Experiment: # <- class name
        exp1: # <- resource ID
            ... # <- resource definition
    Sample: # <- class name
        sample1: # <- resource ID
            ... # <- resource definition
```

*Resource definition* must adhere to the following structure:

* `content`: The content of the resource that complies with the content schema defined in the corresponding schemapack.

    ```yaml

    content: # <- content schema embedded here
        name: Example Resource
        description: This is an example resource.
    ```

* `relations`: A dictionary containing the relations of the resource to other resources. Each key is the name of a relation mapped to their datapack relation definitions. Each value contains the target class and target resource(s) of the relation.

  Relation definition must follow the following structure:

    * `targetClass`:  The name of the referenced class.

    * `targetResources`: The ID(s) of target resources of the targetClass. Based on the schemapack relation definition, this field can have the following values:


    |                             | **mandatory.target = True** | **mandatory.target = False**        |
    | --------------------------- | --------------------------- | ----------------------------------- |
    | **multiple.target = True**  | set of resource IDs         | set of resource IDs or an empty set |
    | **multiple.target = False** | a single ID                 | a single ID or None                 |

    Example:

    ```yaml

    relations:
        samples: # <- relation name
            targetClass: Sample
            targetResources:
                - sample1 # <- resource ID of the target resource
                - sample2 # <- resource ID of another target resource
    ```


A full datapack example:

```yaml
datapack: 3.0.0
resources:
    Experiment:
        exp1:
            content:
                name: Experiment 1
                description: This is the first experiment.
            relations:
                samples:
                    targetClass: Sample
                    targetResources: sample1
        exp2:
            content:
                name: Experiment 2
                description: This is the second experiment.
            relations:
                samples:
                    targetClass: Sample
                    targetResources: sample1
    Sample:
        sample1:
            content:
                name: Sample 1
                description: This is the first sample.
```


`rootResource` *(optional)*: Defines the id of the resource of the class defined in `className` that should act as root. This means that, in addition to the root resource itself, the datapack must only contain resources that are direct or transitive dependencies of the root resource.

`rootClass` *(optional)*: Defines the class name of the resource that should act as root.

> [!IMPORTANT] A rooted datapack requires its corresponding schemapack to be rooted as well. If you're validating a rooted datapack against a schema, make sure that its schemapack counterpart is also rooted.


A full rooted datapack example with its schemapack counterpart:

<table>
<tr>
<th>datapack</th>
<th>schemapack</th>
</tr>
<tr>
<td>

```yaml
datapack: 3.0.0
resources:
    Experiment:
        exp1:
            content:
                name: Experiment 1
                description: This is the first experiment.
            relations:
                samples:
                    targetClass: Sample
                    targetResources: sample1
    Sample:
        sample1:
            content:
                name: Sample 1
                description: This is the first sample.

rootResource: exp1
rootClass: Experiment
```

</td>
<td>

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
rootClass: Experiment
```

</td>
</tr>
</table>
