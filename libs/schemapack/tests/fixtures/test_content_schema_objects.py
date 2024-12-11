# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Objects to create a ClassDefinition object to test content schema load."""

from arcticfreeze import FrozenDict

from schemapack._internals.spec.schemapack import IDSpec

DATASET_ID = IDSpec(propertyName="alias", description=None)

DATASET_DESCRIPTION = "Dataset without relations"

DATASET_CONTENT = FrozenDict(
    {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
        "description": "A file is an object that contains information generated from a process, either an Experiment or an Analysis.",
        "properties": FrozenDict(
            {
                "checksum": FrozenDict({"type": "string"}),
                "filename": FrozenDict({"type": "string"}),
                "format": FrozenDict({"type": "string"}),
                "size": FrozenDict({"type": "integer"}),
            }
        ),
        "required": ("filename", "format", "checksum", "size"),
        "type": "object",
    }
)

DATASET_RELATIONS = FrozenDict({})
