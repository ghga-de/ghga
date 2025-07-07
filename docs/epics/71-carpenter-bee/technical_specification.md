# Metldata Configurable Workflows (Carpenter Bee)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline

The goal of this epic is to implement workflows in metldata. In contrast to the previously used approach the workflows shall not be implemented in Python but be fully configurable. Just like individual transformations, workflows shall consume and produce a pair of schemapack and datapack.

In this epic, the following shall be implemented:

* a yaml-serializable WorkflowDefinition class according to the specification below
* functionality to execute a workflow, given a schemapack, datapack and workflow definition.

### Workflow Language

The workflow shall be specified as indicated by the following examples:

```yaml
- name: some_transformation
  description: some description
  args:
    {} # transformation config
- name: other_transformation
  args:
    {} # ...
```

Originally the data transformation was described in two layers: A _workflow_ comprising _workflow steps_ which correspond to a single transformation, hard coded in Python with a release cycle bound to that of metldata. And a corresponding configuration file configuring each workflow step with the config schema being defined by the transformation executed in the workflow step.

To retain more flexibility the transformations were previously implemented such that they could perform multiple operations of the same type at once, avoiding too frequent changes to the hard coded workflow. With a configurable workflow this can now be relaxed since additional workflow steps can now be added without any development cost. Any "for each" logic shall therefore be removed from the transformations. For example, the previous "delete relation" transformation used to have a config

```yaml
ClassOne: [slot_a, slot_b]
ClassTwo: [slot_k]
ClassThree: [slot_x, slot_y]
```

allowing for multiple slots in multiple classes to be deleted. Following the logic of this workflow language, this would become

```yaml
- name: delete_relation
  args:
    class_name: ClassOne
    relation_name: slot_a
- name: delete_relation
  args:
    class_name: ClassOne
    relation_name: slot_b
# ... followed by three more invocations of the delete_relation transformation
```

To generically solve the frequent use case of executing the same operation on multiple targets, the specification shall allow for simple loops, similarly to the Ansible language as described [here](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_loops.html#using-loops):

```yaml
- name: delete_relation
  description: "Delete relation {{ item.relation_name }} from class {{ item.class }}"
  args:
    class_name: "{{ item.class }}"
    relation_name:  "{{ item.relation_name }}"
  loop:
  - class_name: ClassOne
    relation_name: slot_a
  - class_name: ClassOne
    relation_name: slot_b
  - class_name: ClassTwo
    relation_name: slot_k
  - class_name: ClassThree
    relation_name: slot_x
  - class_name: ClassThree
    relation_name: slot_y
  - class_name: ClassThree
    relation_name: slot_z
```

### Implementation Detail

The processing of workflows shall be implemented in two stages:

1. The resolution of all "loop" specifications by expanding every workflow step precursor with a loop specification into multiple workflow steps.
1. The execution of the workflow steps

#### Expansion of loops

Initially, the loop specifications shall be used to expand every workflow step precursor into (potentially) multiple workflow steps. Templating the loop logic can be achieved using a minimal data model for the initial deserialization of the YAML file, followed by YAML or JSON serialization, templating and re-deserialization into the actual operation models. The initial pre-templating model may be specified as the following hypothetical model hierarchy

```Python
class WorkflowStepBase:
  # Common base model that makes no assumption about the config type and
  # lacks loop specification
  name: str
  description: str
  args: object

class WorkflowStepPrecursor(WorkflowStepBase):
  # Precursor model with loop specification
  loop: list[object] = []

class WorkflowStep[TConfig](WorkflowStepBase):
  # Fully derived workflow step model
  args: TConfig
```

The expansion may be implemented as

```Python
def apply_template(template: str) -> str:
  # some jinja
  ...

def expand_loop(precursor: WorkflowStepPrecursor) -> list[WorkflowStepBase]:
  precursor_json = precursor.json()
  del precursor_json['loop']

  return [
    WorkflowStepBase.model_validate_json(apply_template(precursor_json, item))
    for item in precursor.loop
    ]

def expand_loops(precursors: list[WorkflowPrecursor]) -> list[WorkflowStepBase]:
  ...
```

### Included / Required

### Example

An example that aims to replace the current workflow specification ([ghga.py](https://github.com/ghga-de/metldata/blob/2.1.2/src/metldata/builtin_workflows/ghga_archive.py)) and configuration ([metadata_config.yaml](https://github.com/ghga-de/metadata-config/blob/2.0.0%2B6/configuration/metadata_config.yaml)) i provided [here](./example_workflow.yaml) as part of the epic spec.

## Human Resource/Time Estimation:

Number of sprints required: ?

Number of developers required: ?
