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

"""Validator of data against a given LinkML schema."""

from linkml_runtime.utils.schemaview import SchemaView

from ghga_validator.core.models import ValidationReport
from ghga_validator.plugins.base_plugin import ValidationPlugin


class Validator:
    """
    Validator of data against a given LinkML schema.

    Args:
        schema: Virtual LinkML schema (SchemaView)
        plugins: List of plugins for validation

    """

    def __init__(self, schema: SchemaView, plugins: list[ValidationPlugin]) -> None:
        self._schema = schema
        self._plugins = plugins

    def validate(self, data: dict, target_class: str) -> ValidationReport:
        """
        Validate an object.

        Args:
            data: The object to validate
            target_class: The type of object

        Returns:
            ValidationReport: A validation report that summarizes the validation

        """
        validation_results = [
            plugin.validate(data=data, target_class=target_class)
            for plugin in self._plugins
        ]
        all_valid = all(result.valid for result in validation_results)
        validation_report = ValidationReport(
            object=data,
            type=target_class,
            valid=all_valid,
            validation_results=validation_results,
        )
        return validation_report
