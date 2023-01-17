# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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

"""Unit tests for the core claims module."""

from datetime import datetime

from ghga_service_chassis_lib.utils import DateTimeUTC

from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.core.claims import (
    is_data_steward_claim,
    is_valid_claim,
)
from auth_service.user_management.claims_repository.models.dto import (
    AuthorityLevel,
    Claim,
    VisaType,
)

datetime_utc = DateTimeUTC.construct


def test_is_valid_claim():
    """Test that claims can be checked for validity."""
    claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.RESEARCHER_STATUS,
        visa_value="https://home.org",
        source="https://home.org",
        assertion_date=datetime_utc(2022, 11, 1),
        valid_from=datetime_utc(2022, 11, 15),
        valid_until=datetime_utc(2022, 11, 20),
        creation_date=datetime_utc(2022, 11, 1),
        creation_by="user-id",
    )
    assert is_valid_claim(claim, now=lambda: datetime_utc(2022, 11, 17))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2020, 1, 1))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2022, 11, 7))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2022, 11, 27))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2029, 12, 31))
    claim = claim.copy(update=dict(revocation_date=datetime(2022, 11, 30)))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2020, 1, 1))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2022, 11, 17))
    assert not is_valid_claim(claim, now=lambda: datetime_utc(2029, 12, 31))


def test_is_data_steward_claim():
    """Test that the data steward role can be derived from a claim."""
    good_claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.GHGA_ROLE,
        visa_value="data_steward@some.org",
        source=CONFIG.organization_url,
        assertion_date=datetime_utc(2022, 11, 1),
        asserted_by=AuthorityLevel.SYSTEM,
        valid_from=datetime_utc(2022, 11, 15),
        valid_until=datetime_utc(2022, 11, 20),
        creation_date=datetime_utc(2022, 11, 1),
        creation_by="user-id",
    )
    assert is_data_steward_claim(good_claim)

    bad_claim = good_claim.copy(update=dict(visa_type=VisaType.AFFILIATION_AND_ROLE))
    assert is_data_steward_claim(good_claim)
    bad_claim = good_claim.copy(update=dict(visa_type=VisaType.AFFILIATION_AND_ROLE))
    assert not is_data_steward_claim(bad_claim)
    bad_claim = good_claim.copy(update=dict(source="https://wrong.org"))
    assert not is_data_steward_claim(bad_claim)
    bad_claim = good_claim.copy(update=dict(asserted_by=None))
    assert not is_data_steward_claim(bad_claim)
    bad_claim = good_claim.copy(update=dict(asserted_by=AuthorityLevel.SELF))
    assert not is_data_steward_claim(bad_claim)
    bad_claim = good_claim.copy(update=dict(visa_value="data_inspector"))
    assert not is_data_steward_claim(bad_claim)
    bad_claim = good_claim.copy(update=dict(visa_value=["data_steward@some.org"]))
    assert not is_data_steward_claim(bad_claim)
