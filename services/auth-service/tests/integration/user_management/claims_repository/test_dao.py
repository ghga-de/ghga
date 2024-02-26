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

"""Test user specific DAOs."""

from ghga_service_commons.utils.utc_dates import utc_datetime
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_fixture,
)
from pytest import mark

from auth_service.user_management.claims_repository.deps import (
    get_claim_dao_factory,
    get_config,
)
from auth_service.user_management.claims_repository.models.dto import (
    Claim,
    ClaimFullCreation,
    VisaType,
)


@mark.asyncio
async def test_claim_creation(
    mongodb_fixture,  # noqa: F811
):
    """Test creating a new user claim"""
    claim_dao_factory = get_claim_dao_factory(
        config=get_config(), dao_factory=mongodb_fixture.dao_factory
    )
    claim_dao = await claim_dao_factory.get_claim_dao()

    claim_data = ClaimFullCreation(
        user_id="some-internal-user-id",
        visa_type=VisaType.GHGA_ROLE,
        visa_value="data-steward@ghga.de",
        assertion_date=utc_datetime(2022, 9, 1),
        valid_from=utc_datetime(2022, 10, 1),
        valid_until=utc_datetime(2022, 10, 31),
        source="https://ghga.de",  # type: ignore
        creation_date=utc_datetime(2022, 9, 15),
    )
    claim = await claim_dao.insert(claim_data)
    assert claim and isinstance(claim, Claim)
    assert claim.id is not None
    assert claim.user_id == claim_data.user_id
    assert claim.visa_type == claim_data.visa_type
    assert claim.assertion_date == claim_data.assertion_date
    assert claim.valid_from == claim_data.valid_from
    assert claim.valid_until == claim_data.valid_until
    assert claim.source == claim_data.source
    assert claim.sub_source is None
    assert claim.asserted_by is None
    assert claim.conditions is None
    assert claim.creation_date == claim_data.creation_date
    assert claim.revocation_date is None
