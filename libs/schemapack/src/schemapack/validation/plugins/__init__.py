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

"""Built-In Validation Plugins"""

# shortcuts:
from schemapack.validation.plugins.content_schema import (
    ContentSchemaValidationPlugin,
)
from schemapack.validation.plugins.expected_root import (
    ExpectedRootValidationPlugin,
)
from schemapack.validation.plugins.missing_class import (
    MissingClassSlotValidationPlugin,
)
from schemapack.validation.plugins.missing_origin import (
    MissingMandatoryOriginValidationPlugin,
)
from schemapack.validation.plugins.missing_relations import (
    MissingRelationValidationPlugin,
)
from schemapack.validation.plugins.missing_target import (
    MissingMandatoryTargetValidationPlugin,
)
from schemapack.validation.plugins.multiple_target import (
    MultipleTargetValidationPlugin,
)
from schemapack.validation.plugins.one_to_many_overlap import (
    TargetOverlapValidationPlugin,
)
from schemapack.validation.plugins.target_id import (
    TargetIdValidationPlugin,
)
from schemapack.validation.plugins.unexpected_root import (
    UnexpectedRootValidationPlugin,
)
from schemapack.validation.plugins.unknown_class import (
    UnknownClassSlotValidationPlugin,
)
from schemapack.validation.plugins.unknown_relations import (
    UnknownRelationValidationPlugin,
)
from schemapack.validation.plugins.unkown_root_resource import (
    UnkownRootResourceValidationPlugin,
)

__all__ = [
    "ContentSchemaValidationPlugin",
    "ExpectedRootValidationPlugin",
    "MissingClassSlotValidationPlugin",
    "MissingRelationValidationPlugin",
    "MissingMandatoryTargetValidationPlugin",
    "MultipleTargetValidationPlugin",
    "TargetOverlapValidationPlugin",
    "TargetIdValidationPlugin",
    "UnexpectedRootValidationPlugin",
    "UnknownClassSlotValidationPlugin",
    "UnknownRelationValidationPlugin",
    "UnkownRootResourceValidationPlugin",
    "MissingMandatoryOriginValidationPlugin",
]
