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

"""Logic for running multiple validation plugins on a datapack with respect to a
schemapack.
"""

from typing import overload

from schemapack._internals.validation.base import (
    ClassValidationPlugin,
    GlobalValidationPlugin,
    ResourceValidationPlugin,
)
from schemapack._internals.validation.default import (
    DEFAULT_CLASS_PLUGIN_REGISTRY,
    DEFAULT_GLOBAL_PLUGIN_REGISTRY,
    DEFAULT_RESOURCE_PLUGIN_REGISTRY,
)
from schemapack.exceptions import (
    ValidationError,
    ValidationErrorRecord,
    ValidationPluginError,
)
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack


def _create_global_plugins(
    *, schemapack: SchemaPack, plugin_classes: list[type[GlobalValidationPlugin]]
):
    """Create instances of all the provided global plugins that apply to the given
    schemapack.
    """
    return [
        cls(schemapack=schemapack)
        for cls in plugin_classes
        if cls.does_apply(schemapack=schemapack)
    ]


@overload
def _create_plugins_by_class(
    *, schemapack: SchemaPack, plugin_classes: list[type[ClassValidationPlugin]]
) -> dict[str, list[ClassValidationPlugin]]: ...


@overload
def _create_plugins_by_class(
    *, schemapack: SchemaPack, plugin_classes: list[type[ResourceValidationPlugin]]
) -> dict[str, list[ResourceValidationPlugin]]: ...


def _create_plugins_by_class(
    *,
    schemapack: SchemaPack,
    plugin_classes: list[type[ClassValidationPlugin]]
    | list[type[ResourceValidationPlugin]]
    | list[type[ClassValidationPlugin] | type[ResourceValidationPlugin]],
) -> (
    dict[str, list[ClassValidationPlugin]]
    | dict[str, list[ResourceValidationPlugin]]
    | dict[str, list[ResourceValidationPlugin | ClassValidationPlugin]]
):
    """Create instances of the provided plugins for each class (if relevant) in
    the given schemapack.

    Returns:
        A dictionary mapping class names to the corresponding resource plugin instances.
    """
    return {
        class_name: [
            cls(class_=class_)
            for cls in plugin_classes
            if cls.does_apply(class_=class_)
        ]
        for class_name, class_ in schemapack.classes.items()
    }


def _plugin_error_to_record(
    error: ValidationPluginError,
    *,
    subject_class: str | None = None,
    subject_resource: str | None = None,
) -> ValidationErrorRecord:
    """Convert a ValidationPluginError to a ValidationErrorRecord."""
    return ValidationErrorRecord(
        subject_class=subject_class,
        subject_resource=subject_resource,
        type=error.type_,
        message=error.message,
        details=error.details,
    )


def _run_global_plugins(
    *, datapack: DataPack, plugins: list[GlobalValidationPlugin]
) -> list[ValidationErrorRecord]:
    """Run all the given global plugins on the given datapack."""
    records: list[ValidationErrorRecord] = []

    for plugin in plugins:
        try:
            plugin.validate(datapack=datapack)
        except ValidationPluginError as error:
            records.append(_plugin_error_to_record(error))

    return records


def _run_class_plugins(
    *, datapack: DataPack, plugins: dict[str, list[ClassValidationPlugin]]
) -> list[ValidationErrorRecord]:
    """Run all class plugins on all classes of the given datapack."""
    records: list[ValidationErrorRecord] = []

    for class_name, class_resources in datapack.resources.items():
        for plugin in plugins.get(class_name, []):
            try:
                plugin.validate(class_resources=class_resources, datapack=datapack)
            except ValidationPluginError as error:
                records.append(_plugin_error_to_record(error, subject_class=class_name))

    return records


def _run_resource_plugins(
    *, datapack: DataPack, plugins: dict[str, list[ResourceValidationPlugin]]
) -> list[ValidationErrorRecord]:
    """Run all resource plugins on all resources of all classes of the given datapack."""
    records: list[ValidationErrorRecord] = []

    for class_name, class_resources in datapack.resources.items():
        for resource_id, resource in class_resources.items():
            for plugin in plugins.get(class_name, []):
                try:
                    plugin.validate(
                        resource_id=resource_id, resource=resource, datapack=datapack
                    )
                except ValidationPluginError as error:
                    records.append(
                        _plugin_error_to_record(error, subject_class=class_name)
                    )

    return records


class SchemaPackValidator:
    """A class for validating arbitrary datapacks against a specific schemapack."""

    def __init__(
        self,
        *,
        schemapack: SchemaPack,
        add_global_plugins: list[type[GlobalValidationPlugin]] | None = None,
        add_class_plugins: list[type[ClassValidationPlugin]] | None = None,
        add_resource_plugins: list[type[ResourceValidationPlugin]] | None = None,
    ):
        """Initialize with a specific schemapack.

        Args:
            schemapack:
                The schemapack to validate against.
            add_global_plugins:
                Global validation plugins to use in addition to the default ones.
            add_class_plugins:
                Class validation plugins to use in addition to the default ones.
            add_resource_plugins:
                Resource validation plugins to use in addition to the default ones.
        """
        self._global_plugins = _create_global_plugins(
            schemapack=schemapack,
            plugin_classes=DEFAULT_GLOBAL_PLUGIN_REGISTRY + (add_global_plugins or []),
        )
        self._class_plugins = _create_plugins_by_class(
            schemapack=schemapack,
            plugin_classes=DEFAULT_CLASS_PLUGIN_REGISTRY + (add_class_plugins or []),
        )
        self._resource_plugins = _create_plugins_by_class(
            schemapack=schemapack,
            plugin_classes=DEFAULT_RESOURCE_PLUGIN_REGISTRY
            + (add_resource_plugins or []),
        )

    def validate(self, *, datapack: DataPack):
        """Validates the given datapack against the configured schemapack. The execution
        order of validation plugins is as follows:
        (1) Run global validation plugins
        (2) Only upon success, execute class validation plugins.
        (3) Only upon success, run resource validation plugins.
        The reason for this conditional execution is that class plugins are assuming a
        intact state on the global level. Similarly, resource plugins are assuming an
        intact state on the class level.

        Raises:
            schemapack.exceptions.ValidationError: If any validation issues are found.
        """
        error_records = _run_global_plugins(
            datapack=datapack, plugins=self._global_plugins
        )

        if not error_records:
            error_records.extend(
                _run_class_plugins(datapack=datapack, plugins=self._class_plugins)
            )

            if not error_records:
                error_records.extend(
                    _run_resource_plugins(
                        datapack=datapack, plugins=self._resource_plugins
                    )
                )

        if error_records:
            raise ValidationError(records=error_records)
