# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Base classes for defining validation plugins."""

from abc import ABC, abstractmethod
from collections.abc import Mapping

from schemapack.spec.custom_types import ResourceId
from schemapack.spec.datapack import DataPack, Resource
from schemapack.spec.schemapack import ClassDefinition, SchemaPack


class GlobalValidationPlugin(ABC):
    """Abstract class for a plugin that performs validation of a datapack with respect
    to the entire schemapack.

    Please note:
    A ValidationPlugin should always just check for one single aspect of validation
    and should not perform all checks possible with a schemapack.
    The "global" scope only means that objects implementing this protocol do not focus
    on one specific datapack class or resource but rather on a validation
    aspect that applies to the entire datapack.
    """

    @staticmethod
    @abstractmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given schemapack.
        """
        raise NotImplementedError

    @abstractmethod
    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        raise NotImplementedError


class ClassValidationPlugin(ABC):
    """Abstract class for defining class-scoped validation plugin. Instances
    of implemeting concrete classes perform validation with respect to one
    specific schemapack class.
    """

    @staticmethod
    @abstractmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given class definition.

        Returns: True if this plugin is relevant for the given class definition.
        """
        raise NotImplementedError

    @abstractmethod
    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        raise NotImplementedError

    @abstractmethod
    def validate(
        self, *, class_resources: Mapping[ResourceId, Resource], datapack: DataPack
    ):
        """Validate all resources of a specific class. The entire datapack is provided
        for resolving relations to other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        raise NotImplementedError


class ResourceValidationPlugin(ABC):
    """Abstract class for defining resource-scoped validation plugin. Implementing
    objects perform validation with respect to one specific resource of a schemapack
    class.
    """

    @staticmethod
    @abstractmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given class definition.

        Returns: True if this plugin is relevant for the given class definition.
        """
        raise NotImplementedError

    @abstractmethod
    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        raise NotImplementedError

    @abstractmethod
    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ) -> None:
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        raise NotImplementedError
