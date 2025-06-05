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

"""Exit codes returned for different outcomes."""

from typing import Final

SUCCESS: Final = 0
VALIDATION_ERROR: Final = 10
DATAPACK_SPEC_ERROR: Final = 20
SCHEMAPACK_SPEC_ERROR: Final = 30
CLASS_NOT_FOUND_ERROR: Final = 40
RESOURCE_NOT_FOUND_ERROR: Final = 41
