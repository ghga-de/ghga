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

"""Unit tests for the core claims module."""

from datetime import datetime

from ghga_service_commons.utils.utc_dates import now_as_utc, utc_datetime

from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.core.claims import (
    create_controlled_access_claim,
    create_data_steward_claim,
    dataset_id_for_download_access,
    get_dataset_for_value,
    has_download_access_for_dataset,
    is_data_steward_claim,
    is_internal_claim,
    is_valid_claim,
)
from auth_service.user_management.claims_repository.models.claims import (
    AuthorityLevel,
    Claim,
    VisaType,
)

ORG_URL = str(CONFIG.organization_url).rstrip("/")


def test_is_valid_claim():
    """Test that claims can be checked for validity regarding expiry."""
    claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.RESEARCHER_STATUS,
        visa_value="https://home.org",
        source="https://home.org",  # type: ignore
        assertion_date=utc_datetime(2022, 11, 1),
        valid_from=utc_datetime(2022, 11, 15),
        valid_until=utc_datetime(2022, 11, 20),
        creation_date=utc_datetime(2022, 11, 1),
    )
    assert is_valid_claim(claim, now=lambda: utc_datetime(2022, 11, 17))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2020, 1, 1))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2022, 11, 7))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2022, 11, 27))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2029, 12, 31))
    claim = claim.model_copy(update={"revocation_date": datetime(2022, 11, 30)})
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2020, 1, 1))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2022, 11, 17))
    assert not is_valid_claim(claim, now=lambda: utc_datetime(2029, 12, 31))


def test_is_internal_claim():
    """Test that the validity check for internal claims works."""
    good_claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.GHGA_ROLE,
        visa_value="data_steward@some.org",
        source=CONFIG.organization_url,
        assertion_date=utc_datetime(2022, 11, 1),
        asserted_by=AuthorityLevel.SYSTEM,
        valid_from=utc_datetime(2022, 11, 15),
        valid_until=utc_datetime(2022, 11, 20),
        creation_date=utc_datetime(2022, 11, 1),
    )
    assert is_internal_claim(good_claim, VisaType.GHGA_ROLE)
    assert not is_internal_claim(good_claim, VisaType.RESEARCHER_STATUS)

    def check_tampered_claim(**kwargs):
        bad_claim = good_claim.model_copy(update=kwargs)
        return not is_internal_claim(bad_claim, VisaType.GHGA_ROLE)

    assert check_tampered_claim(source="https://wrong.org")
    assert check_tampered_claim(asserted_by=None)
    assert check_tampered_claim(asserted_by=AuthorityLevel.SELF)


def test_create_data_steward_claim():
    """Test that a data steward claim can be created."""
    created_claim = create_data_steward_claim(
        user_id="some-user-id", iva_id="some-claim_id"
    )
    assert created_claim.user_id == "some-user-id"
    assert created_claim.iva_id == "some-claim_id"
    full_claim = Claim(id="some-claim-id", **created_claim.model_dump())
    assert is_valid_claim(full_claim)
    assert is_data_steward_claim(full_claim)
    assert not has_download_access_for_dataset(full_claim, "DS0815")


def test_is_data_steward_claim():
    """Test that the data steward role can be derived from a claim."""
    good_claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.GHGA_ROLE,
        visa_value="data_steward@some.org",
        source=CONFIG.organization_url,
        assertion_date=utc_datetime(2022, 11, 1),
        asserted_by=AuthorityLevel.SYSTEM,
        valid_from=utc_datetime(2022, 11, 15),
        valid_until=utc_datetime(2022, 11, 20),
        creation_date=utc_datetime(2022, 11, 1),
    )
    assert is_data_steward_claim(good_claim)

    def check_tampered_claim(**kwargs):
        bad_claim = good_claim.model_copy(update=kwargs)
        return not is_data_steward_claim(bad_claim)

    assert check_tampered_claim(visa_type=VisaType.AFFILIATION_AND_ROLE)
    assert check_tampered_claim(source="https://wrong.org")
    assert check_tampered_claim(asserted_by=None)
    assert check_tampered_claim(asserted_by=AuthorityLevel.SELF)
    assert check_tampered_claim(visa_value="data_inspector")
    assert check_tampered_claim(visa_value=["data_steward@some.org"])


def test_create_controlled_access_claim():
    """Test that a controlled access claim can be created."""
    current_year = now_as_utc().year
    created_claim = create_controlled_access_claim(
        user_id="some-user-id",
        iva_id="some-iva-id",
        dataset_id="DS0815",
        valid_from=utc_datetime(current_year - 1, 7, 1),
        valid_until=utc_datetime(current_year + 1, 6, 30),
    )
    assert created_claim.user_id == "some-user-id"
    assert created_claim.iva_id == "some-iva-id"
    assert get_dataset_for_value(str(created_claim.visa_value)) == "DS0815"
    full_claim = Claim(id="some-claim-id", **created_claim.model_dump())
    assert is_valid_claim(full_claim)
    assert not is_data_steward_claim(full_claim)
    assert has_download_access_for_dataset(full_claim, "DS0815")
    assert dataset_id_for_download_access(full_claim) == "DS0815"


def test_get_dataset_for_value():
    """Test that a dataset id for a visa value can be created."""
    assert get_dataset_for_value(f"{ORG_URL}/datasets/DS0815") == "DS0815"


def test_has_download_access_for_dataset():
    """Test that the dataset access permission can be derived from a claim."""
    good_claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
        visa_value=f"{ORG_URL}/datasets/DS0815",  # pyright: ignore
        source=ORG_URL,  # type: ignore[arg-type]
        sub_source=None,
        assertion_date=utc_datetime(2022, 11, 1),
        asserted_by=AuthorityLevel.SYSTEM,
        valid_from=utc_datetime(2022, 11, 15),
        valid_until=utc_datetime(2022, 11, 20),
        creation_date=utc_datetime(2022, 11, 1),
        revocation_date=None,
        conditions=None,
    )
    assert has_download_access_for_dataset(good_claim, "DS0815")
    assert not has_download_access_for_dataset(good_claim, "DS0816")

    def check_tampered_claim(**kwargs):
        bad_claim = good_claim.model_copy(update=kwargs)
        return not has_download_access_for_dataset(bad_claim, "DS0815")

    assert check_tampered_claim(visa_type=VisaType.ACCEPTED_TERMS_AND_POLICIES)
    assert check_tampered_claim(source="https://wrong.org")
    assert check_tampered_claim(asserted_by=None)
    assert check_tampered_claim(asserted_by=AuthorityLevel.SELF)
    assert check_tampered_claim(visa_value="data_inspector")
    assert check_tampered_claim(visa_value="https://another.org/datasets/DS0815")
    assert check_tampered_claim(visa_value=[f"{ORG_URL}/datasets/DS0815"])


def test_dateset_id_when_download_access():
    """Test that the dataset ID for access can be derived from a claim."""
    good_claim = Claim(
        id="claim-id",
        user_id="user-id",
        visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
        visa_value=f"{ORG_URL}/datasets/DS0815",  # pyright: ignore
        source=ORG_URL,  # type: ignore[arg-type]
        sub_source=None,
        assertion_date=utc_datetime(2022, 11, 1),
        asserted_by=AuthorityLevel.SYSTEM,
        valid_from=utc_datetime(2022, 11, 15),
        valid_until=utc_datetime(2022, 11, 20),
        creation_date=utc_datetime(2022, 11, 1),
        revocation_date=None,
        conditions=None,
    )
    assert dataset_id_for_download_access(good_claim) == "DS0815"

    def check_tampered_claim(**kwargs):
        bad_claim = good_claim.model_copy(update=kwargs)
        return dataset_id_for_download_access(bad_claim) is None

    assert check_tampered_claim(visa_type=VisaType.ACCEPTED_TERMS_AND_POLICIES)
    assert check_tampered_claim(source="https://wrong.org")
    assert check_tampered_claim(asserted_by=None)
    assert check_tampered_claim(asserted_by=AuthorityLevel.SELF)
    assert check_tampered_claim(visa_value="data_inspector")
    assert check_tampered_claim(visa_value="https://another.org/datasets/DS0815")
    assert check_tampered_claim(visa_value=[f"{ORG_URL}/datasets/DS0815"])
