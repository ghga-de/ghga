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
from schemapack.validation.plugins.cardinality_plural import (
    CardinalityPluralityValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.content_schema import (
    ContentSchemaValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.duplicate_foreign_id import (
    DuplicateForeignIdValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.expected_root import (
    ExpectedRootValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.foreign_id import (
    ForeignIdValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.missing_class import (
    MissingClassSlotValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.missing_relations import (
    MissingRelationValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.one_to_many_overlap import (
    OneToManyOverlapValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.one_to_one_overlap import (
    OneToOneOverlapValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.unexpected_root import (
    UnexpectedRootValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.unknown_class import (
    UnknownClassSlotValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.unknown_relations import (
    UnknownRelationValidationPlugin,  # noqa: F401
)
from schemapack.validation.plugins.unkown_root_resource import (
    UnkownRootResourceValidationPlugin,  # noqa: F401
)
