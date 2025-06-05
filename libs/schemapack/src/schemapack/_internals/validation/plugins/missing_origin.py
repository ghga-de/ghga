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

"""A validation plugin."""

from collections.abc import Mapping

from schemapack._internals.validation.base import ClassValidationPlugin
from schemapack.exceptions import ValidationPluginError
from schemapack.spec.custom_types import ResourceId
from schemapack.spec.datapack import DataPack, Resource
from schemapack.spec.schemapack import ClassDefinition


class MissingMandatoryOriginValidationPlugin(ClassValidationPlugin):
    """A class-scoped validation plugin validating that every target resource is
    referenced by at least one origin resource for relations that are mandatory at the
    origin end.

    This only applies to schemapacks classes with relations that are mandatory at the
    origin end.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return any(relation.mandatory.origin for relation in class_.relations.values())

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._relations_of_interest = {
            relation_name: relation
            for relation_name, relation in class_.relations.items()
            if relation.mandatory.origin
        }

    def validate(
        self, *, class_resources: Mapping[ResourceId, Resource], datapack: DataPack
    ):
        """Validate all resources of a specific class. The entire datapack is provided
        for resolving relations to other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        not_referenced_target_id_by_relation: dict[str, set[str]] = {}

        for relation_name, relation in self._relations_of_interest.items():
            try:
                referenced_target_ids = {
                    target_id
                    for resource in class_resources.values()
                    for target_id in resource.relations[
                        relation_name
                    ].get_target_resources_as_set()
                }
            except KeyError:
                referenced_target_ids = set()

            all_possible_target_ids = set(
                datapack.resources.get(relation.targetClass, {})
            )

            not_referenced_target_ids = all_possible_target_ids.difference(
                referenced_target_ids
            )
            if not_referenced_target_ids:
                not_referenced_target_id_by_relation[relation_name] = (
                    not_referenced_target_ids
                )

        if any(not_referenced_target_id_by_relation.values()):
            raise ValidationPluginError(
                type_="MissingMandatoryOriginError",
                message=(
                    "For the following relations that are mandatory on the origin end"
                    + " the specified targets are not referenced by any origin:"
                    + f"{not_referenced_target_id_by_relation}"
                ),
                details={
                    "not_referenced_target_by_relation": not_referenced_target_id_by_relation
                },
            )
