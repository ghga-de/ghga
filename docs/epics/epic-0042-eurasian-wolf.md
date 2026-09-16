# Custom Specification Separating Schema Validation and Schema Linkage (Eurasian Wolf)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
The aim of this epic is to implement a proof of concept for a specification that separates schema validation and schema linkage
as prototyped [here](https://github.com/ghga-de/metadata_schema_explorations).


### Included/Required:
- basic validation of:
  - content schemas
  - uniqueness of ID
  - resource relations including cardinality
- isolation of individual resources incl. references
- integration of references into individual resources
- re-implementation of a simple metldata workflow, including:
  - reference inference
  - slot deletion
  - isolation of individual resources
  - integration of individual resources
- performance documentation but not optimization



## Additional Details:

### Validation:

Content validation will be done using JSON schemas as demonstrated
[here](https://github.com/ghga-de/metadata_schema_explorations/blob/main/schema/schemapack.yaml#L7).
The validation of relationships will follow specifications as demonstrated
[here](https://github.com/ghga-de/metadata_schema_explorations/blob/main/schema/schemapack.yaml#L17).
Only the lookup method "in-document" is supported.

Data is structured with content and resources being separated as demonstrated
[here](https://github.com/ghga-de/metadata_schema_explorations/blob/main/data/desintegrated.yaml#L33-L41).

The uniqueness of IDs is only checked among the instances of one class.

Uniqueness constraints as demonstrated
[here](https://github.com/ghga-de/metadata_schema_explorations/blob/main/schema/schemapack.yaml#L9-L12)
are ignored by the POC.

Support for validating both rooted (as shown [here](https://github.com/ghga-de/metadata_schema_explorations/blob/main/data/desintegrated.yaml#L42-L44))
and non-rooted documents will be implemented.


### Isolation and Integration of Resources:

Tooling for creating multiple rooted documents, which focus on an individual resource,
from a non-rooted document will be implemented.

So prepared rooted documents can then be integrated to result in an ordinary JSON
document that has its references embedded. This process may be configured by
providing a so-called embedding profile to control which references are included.

The reverse transformation from an integrated to a non-integrated document is not
part of this POC.

### Re-implementation of a Simple Metldata Workflow:

Only the transformations for reference inference and slot deletion will be required for
this POC.

Transformations dealing with the embedding of resources are replaced with the tooling
for isolation and integration as described above.

Transformation workflows need to distinguish between operations that are performed
on the entire submission (i.e. non-rooted documents) and operations that are applied
to single resources (i.e. rooted documents after isolation). Moreover, integration steps
can be seen as a third operation category. However, integrations always mark the end
of a transformation workflow.

### Performance Documentation:

Simple performance metrics such as execution time will be recorded to assess the
general feasibility of the approach. No performance optimization should be performed.
However, performance might be a criterion for selecting dependencies for this POC.


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
