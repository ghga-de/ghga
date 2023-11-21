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

"""Reference models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from metldata.builtin_transformations.infer_references.path.path import ReferencePath


class ReferenceDetails(BaseModel):
    """A base model for describing an inferred reference that is based on existing
    references.
    """

    path: ReferencePath = Field(
        ...,
        description="The path to reconstruct the new reference based on existing references.",
    )
    multivalued: bool = Field(
        ..., description="Whether the new reference will be multivalued."
    )


class InferredReference(ReferenceDetails):
    """A model for describing an inferred reference that is based on existing
    references.
    """

    model_config = ConfigDict(frozen=True)

    source: str = Field(
        ..., description="The source class to which this reference should be added."
    )
    target: str = Field(..., description="The class targeted by this reference.")
    new_slot: str = Field(
        ...,
        description="The name of the new slot in the source to store the inferred reference.",
    )

    @model_validator(mode="after")
    @classmethod
    def validate_source_and_target(cls, values):
        """Validate that the source and target attributes are identical with the
        source and target specified in the path.
        """
        if values.source != values.path.source:
            raise ValueError(
                "The source is not identical with the source of the specified path."
            )

        if values.target != values.path.target:
            raise ValueError(
                "The target is not identical with the target of the specified path."
            )

        return values
