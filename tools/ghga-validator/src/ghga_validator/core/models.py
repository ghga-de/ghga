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

"""Collection of classes for modelling validation results"""

from typing import Any, Optional

from pydantic import BaseModel


class ValidationMessage(BaseModel):
    """ValidationMessage represents a validation error message"""

    field: Optional[str] = None
    value: Optional[Any] = None
    message: str


class ValidationResult(BaseModel):
    """
    ValidationResult represents the results of validation
    by a plugin.
    """

    plugin_name: str
    valid: bool
    validation_messages: list[ValidationMessage] = []


class ValidationReport(BaseModel):
    """
    ValidationReport represents the overall validation result by all plugins
    for a given object.
    """

    object: Optional[dict]
    type: str
    valid: bool
    validation_results: list[ValidationResult]
