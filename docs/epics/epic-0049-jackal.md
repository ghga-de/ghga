# Re-Implementation of the Metadata Schema in Schemapack (Jackal)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
Reimplement the metadata model, currently implemented in LinkML, using schemapack.
This should be used to onboard the metadata team and illustrate the use of schemapack for our purposes.
Thereafter, the metadata team should be enabled to drive the metadata model further independently.


### Included/Required:
I. Re-implement the entire LinkML-based model in schemapack  
II. Autogeneration of mermaid-based ER diagrams from a schemapack definition  
III. Transpile schemapack-based models to a spreadsheet representation

## Implementation Details:

### I. Schemapack-based re-implementation of the Metadata Model:
- The schemapack version 0.2.0 should be used.
- following algorithm might streamline the migration:
  1. Transpile the LinkML model to JSON Schema.
  2. Using a script, isolate idividual classes into their own files.
  3. Write a config file (e.g. in json; possibly even automatically extract from LinkML)
     that lists all the relation properties by class.
  4. Write a script that removes the relation properties defined in step 3 from the JSON schemas
     derived in step 2. The resulting JSON schemas can serve as content schemas to be referenced
     by the schemapack generated in next step.
  5. Write a script that automatically generates a schemapack definition using the Class and relation
     information inferred from the intermediary JSON Schemas produced in step 2 and the config
     specified in step 3. Also migrate existing identifier and relation descriptions.
  6. Manually curate modalities and cardinalities in the schemapack generated in step 5.
  7. Make sure the scripts used to successfully migrate to schemapack are persisted in the
     git history.
  8. Cleanup by removing:
     - the LinkML model
     - the migration scripts and configs
     - all intermediary artifacts
  9. Automatically generate ER diagrams and markdown descriptions to document the model
     (checked by CI).
  11. Automatically transpile the schemapack definition to an excel speadsheet template
      (checked by CI).
  12. Add one or multiple example submission (datapacks) that conform to the schemapack;
      in addition to serving as documentation, they should be used in automatic
      tests to validate the behavior of the metadata model (and act as a change
      detector to alert everybody that the model behavior has changed so that
      the submission datapacks need to adapt). The examples from the
      [example-data](https://github.com/ghga-de/example-data) repository
      might be used but have to be transformed to datapack.
  13. Refactor the directory structure to adapt to the new implementation

### II. Autogeneration of mermaid-based ER diagrams from a schemapack definition:
- To be implemented into the schemapack library with a dedicated CLI command
- The mermaid language is used as output (visualization must be performed
  elsewhere)
- The following example schemapack:
  ```yaml
  schemapack: 0.2.0
  description: A simple schemapack # with no root class but with descriptions.
  classes:
    File:
      id:
        propertyName: alias
      content: ../../content_schemas/File.schema.json
    Dataset:
      id:
        propertyName: alias
      content: ../../content_schemas/Dataset.schema.json
      relations:
        files:
          targetClass: File
          mandatory:
            origin: true
            target: true
          multiple:
            origin: true
            target: true
    ```
- Should be transpiled to mermaid as:
  ```
  erDiagram
      File }|--|{ Dataset: "Dataset.files"
      Dataset {
          string dac_contact
      }
      File {
          string filename
          string format
          string checksum
          int size
      }
  ```
- visualized as (e.g. view this on GitHub for the diagram to be automatically rendered):
  ```mermaid
  erDiagram
      File }|--|{ Dataset: "Dataset.files"
      Dataset {
          string dac_contact
      }
      File {
          string filename
          string format
          string checksum
          int size
      }
  ```
- In agreement with the schemapack concept, there
  is a clear separation between content properties and
  relations:
  - content properties are shown as attributes of the
    entities
  - relations are shown as arrows connecting entities
- the name of the arrows are composed of the name of
  the class defining the relation and the name of the
  relation property; this makes the directionality of
  the relation clear
- crow foot notation is used to adequately model both
  the modality (`mandatory` specs in schemapack) and
  the cardinality (`multiple` specs in schemapack),
  please see https://vertabelo.com/blog/crow-s-foot-notation/
  for further details
- Since schemapack makes no assumption about content
  schemas of individual classes (except that they
  discribe JSON object), not every content schema can
  be fully visualized. Thus only the properties of
  the top-level object of the content schema should be
  visualized. Thereby, non-primitive types (including
  properties that define nested structures such as
  further objects or arrays) are annotated with the type
  "Custom".
- There should also be an option to skip content
  information from the diagram, like that:
  ```
  erDiagram
      File }|--|{ Dataset: "Dataset.files"
      Dataset {}
      File {}
  ```
- Which is visualized as:
  ```mermaid
  erDiagram
      File }|--|{ Dataset: "Dataset.files"
      Dataset {}
      File {}
  ```
### III. Refactor ghga-transpiler

- Make transpiler produce datapack instead of original JSON format
- Migrate ghga-transpiler to a more general configuration strategy that ideally lives longer than individual metadata models
  - Refactor the transpiler to read the infomation on i) the data types (e.g., list, str, int), ii) the value restriction (unrestricted, controlled vocabulary, value from another class) from a hidden sheet in the XLS file. This information will be presented in table form with boolean values.
  - Refactor the transpiler to read the second hidden sheet where the indices of the header row, start row, and start column are provided; and a third hidden sheet where the version of the transpilation protocol is encoded.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 3
