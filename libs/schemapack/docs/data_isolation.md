<!--
 Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
 for the German Human Genome-Phenome Archive (GHGA)

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

# Data Isolation

The Schemapack library provides tooling to isolate individual resources and their dependencies from larger datasets. This is useful for partial extraction, targeted validation, or incremental processing.

It creates a rooted datapack that contains only the specified resource and all its dependencies, e.g., the resulting datapack will only contain resources referenced by the root resource as well as the root resource itself.

> [!IMPORTANT] The isolated datapack will not be compatible with the original non-rooted schemapack anymore.


Example

```bash
schemapack isolate-resource \
    --schemapack ./examples/example_schemapack.yaml \
    --datapack ./examples/example_datapack.yaml \
    --class-name Experiment \
    --resource-id exp1 \
```

Isolated output for class `Experiment` and resource `exp1`:


```yaml
datapack: 3.0.0
resources:
  Sample:
    sample1:
      content:
        name: Sample 1
        description: This is the first sample.
  Experiment:
    exp1:
      content:
        name: Experiment 1
        description: This is the first experiment.
      relations:
        samples:
          targetClass: Sample
          targetResources:
            - sample1
rootResource: exp1
rootClass: Experiment
```
