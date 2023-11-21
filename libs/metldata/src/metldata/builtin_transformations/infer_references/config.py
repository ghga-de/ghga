# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Models used to describe all inferred references based on existing references."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from metldata.builtin_transformations.infer_references.reference import (
    InferredReference,
    ReferenceDetails,
)


class ReferenceInferenceConfig(BaseSettings):
    """Config containing inferred references for all classes of a metadata model in a
    dictionary-based representation and the option to translate that reference map into
    a list of InferredReferences.
    """

    model_config = SettingsConfigDict(extra="forbid")

    inferred_ref_map: dict[str, dict[str, ReferenceDetails]] = Field(
        ...,
        description=(
            "A nested dictionary describing inferred references based"
            + " on existing references. On the first level keys refer to classes to"
            + " which inferred references should be added. On the second level, keys"
            + " refer to the names of the new slots of classes that hold the inferred"
            + " references. The values refer to the actual references details."
        ),
        examples=[
            {
                "class_a": {
                    "class_d": {
                        "path": "class_a(class_b)>class_b(class_d)>class_d",
                        "multivalued": False,
                    },
                    "class_c": {
                        "path": "class_a(class_b)>class_b<(class_c)class_c",
                        "multivalued": True,
                    },
                },
                "class_b": {
                    "class_c": {
                        "path": "class_b<(class_c)class_c",
                        "multivalued": True,
                    }
                },
            }
        ],
    )

    @property
    def inferred_references(self) -> list[InferredReference]:
        """A list of inferred references."""
        inferred_refs: list[InferredReference] = []

        for source, slot_description in self.inferred_ref_map.items():
            for new_slot, reference_details in slot_description.items():
                target = reference_details.path.target
                inferred_refs.append(
                    InferredReference(
                        source=source,
                        target=target,
                        path=reference_details.path,
                        new_slot=new_slot,
                        multivalued=reference_details.multivalued,
                    )
                )

        return inferred_refs
