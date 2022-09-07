# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

from datetime import datetime

from hexkit.providers.mongodb.testutils import (  # noqa: F401; pylint: disable=unused-import
    mongodb_fixture,
)
from pytest import mark

from auth_service.user_management.api.deps import (
    get_config,
    get_user_dao_factory,
    get_user_dao_factory_config,
)
from auth_service.user_management.ports.dto import (
    AcademicTitle,
    UserCreationDto,
    UserDto,
)


@mark.asyncio
async def test_user_creation(mongodb_fixture):  # noqa: F811
    """Test creating a new user"""

    config = get_config()
    user_dao_factory_config = get_user_dao_factory_config(config=config)
    user_dao_factory = get_user_dao_factory(
        config=user_dao_factory_config, dao_factory=mongodb_fixture.dao_factory
    )
    user_dao = await user_dao_factory.get_user_dao()

    user_creation_dto = UserCreationDto(
        ls_id="max@ls.org",
        name="Max Headroom",
        email="max@example.org",
        academic_title=AcademicTitle.DR,
        research_topics="genes",
        registration_reasons="for testing",
        registration_date=datetime(2022, 9, 1, 12, 0),
    )
    user_dto = await user_dao.insert(user_creation_dto)
    assert user_dto and isinstance(user_dto, UserDto)
    assert user_dto.ls_id == user_creation_dto.ls_id
    assert user_dto.name == user_creation_dto.name
    assert user_dto.email == user_creation_dto.email
    assert user_dto.academic_title == user_creation_dto.academic_title
    assert user_dto.research_topics == user_creation_dto.research_topics
    assert user_dto.registration_reason == user_creation_dto.registration_reason
    assert user_dto.registration_date == user_creation_dto.registration_date
    id_ = user_dto.id
    assert id_ and isinstance(id_, str)
