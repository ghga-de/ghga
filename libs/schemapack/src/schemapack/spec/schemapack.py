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
#

"""Models representing the schemapack spec (part of the public API of this package)."""

from schemapack._internals.spec.schemapack import (
    SUPPORTED_SCHEMA_PACK_VERSIONS,
    ClassDefinition,
    IDSpec,
    MandatoryRelationSpec,
    MultipleRelationSpec,
    Relation,
    SchemaPack,
    SupportedSchemaPackVersions,
)

__all__ = [
    "SUPPORTED_SCHEMA_PACK_VERSIONS",
    "SchemaPack",
    "ClassDefinition",
    "IDSpec",
    "MandatoryRelationSpec",
    "MultipleRelationSpec",
    "Relation",
    "SupportedSchemaPackVersions",
]
