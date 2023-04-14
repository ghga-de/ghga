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

"""Models to describe transformations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel, Field

from metldata.custom_types import Json

# shortcuts:
# pylint: disable=unused-import
from metldata.model_utils.assumptions import MetadataModelAssumptionError  # noqa: F401
from metldata.model_utils.essentials import MetadataModel


class MetadataModelTransformationError(RuntimeError):
    """Raised when a transformation failed when applied to the metadata model."""


class MetadataTransformationError(RuntimeError):
    """Raised when a transformation failed when applied to metadata."""


Config = TypeVar("Config", bound=BaseModel)


class MetadataTransformer(ABC, Generic[Config]):
    """A base class for a metadata transformer."""

    def __init__(
        self,
        *,
        config: Config,
        original_model: MetadataModel,
        transformed_model: MetadataModel
    ):
        """Initialize the transformer with config params, the original model, and the
        transformed model."""

        self._config = config
        self._original_model = original_model
        self._transformed_model = transformed_model

    @abstractmethod
    def transform(self, *, metadata: Json) -> Json:
        """Transforms metadata.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """
        ...


@dataclass(frozen=True)
class TransformationDefinition(Generic[Config]):
    """A model for describing a transformation."""

    config_cls: type[Config] = Field(
        ..., description="The config model of the transformation."
    )
    check_model_assumptions: Callable[[MetadataModel, Config], None] = Field(
        ...,
        description=(
            "A function that checks the assumptions made about the input model."
            "Raises a MetadataModelAssumptionError if the assumptions are not met."
        ),
    )
    transform_model: Callable[[MetadataModel, Config], MetadataModel] = Field(
        ...,
        description=(
            "A function to transform the model. Raises a"
            + " MetadataModelTransformationError if the transformation fails."
        ),
    )
    metadata_transformer_factory: type[MetadataTransformer[Config]] = Field(
        ...,
        description=(
            "A class for transforming metadata. Raises a MetadataTransformationError"
            "if the transformation fails."
        ),
    )
