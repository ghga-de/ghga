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

"""DAO translators for accessing the database."""

from hexkit.protocols.dao import DaoFactoryProtocol

from wps.core import models
from wps.ports.outbound.dao import WorkPackageDaoPort


class WorkPackageDaoConstructor:
    """Constructor compatible with the hexkit.inject.AsyncConstructable type.

    Used to construct a DAO for work packages.
    """

    @staticmethod
    async def construct(
        *, name: str, dao_factory: DaoFactoryProtocol
    ) -> WorkPackageDaoPort:
        """Setup the DAOs using the specified provider of the
        DaoFactoryProtocol."""

        return await dao_factory.get_dao(
            name=name,
            dto_model=models.WorkPackage,
            dto_creation_model=models.WorkPackageData,
            id_field="id",
        )
