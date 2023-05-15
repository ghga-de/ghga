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

"""
Definitions and helper functions for validating user claims.
"""

from datetime import timedelta
from typing import Callable, Optional

from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc
from pydantic import EmailStr, HttpUrl, parse_obj_as

from ....config import CONFIG
from ..models.dto import AuthorityLevel, Claim, ClaimFullCreation, VisaType

__all__ = [
    "create_controlled_access_claim",
    "create_data_steward_claim",
    "dataset_id_for_download_access",
    "is_valid_claim",
    "is_internal_claim",
    "is_data_steward_claim",
    "get_dataset_for_value",
    "has_download_access_for_dataset",
]


INTERNAL_SOURCE = CONFIG.organization_url
INTERNAL_DOMAIN = INTERNAL_SOURCE.split("://", 1)[-1]
DATA_STEWARD_ROLE = "data_steward"
DATASET_PREFIX = f"{INTERNAL_SOURCE}/datasets/"


def is_valid_claim(claim: Claim, now: Callable[[], DateTimeUTC] = now_as_utc) -> bool:
    """Check whether the given claim is currently valid."""
    return not claim.revocation_date and claim.valid_from <= now() <= claim.valid_until


def is_internal_claim(claim: Claim, visa_type: VisaType) -> bool:
    """Check whether this is a valid internal claim of the given type."""
    return (
        claim.visa_type == visa_type
        and claim.source == INTERNAL_SOURCE
        and claim.asserted_by not in (None, AuthorityLevel.SELF)
        # conditions are currently not supported,
        # so if they exist the claim must be considered invalid
        and not claim.conditions
    )


# Data Steward Claims


def create_data_steward_claim(user_id: str, valid_days=365) -> ClaimFullCreation:
    """Create a claim for a data steward."""
    valid_from = now_as_utc()
    valid_until = now_as_utc() + timedelta(days=valid_days)
    return ClaimFullCreation(
        visa_type=VisaType.GHGA_ROLE,
        visa_value=parse_obj_as(EmailStr, f"{DATA_STEWARD_ROLE}@{INTERNAL_DOMAIN}"),
        assertion_date=valid_from,
        valid_from=valid_from,
        valid_until=valid_until,
        source=INTERNAL_SOURCE,
        sub_source=None,
        asserted_by=AuthorityLevel.SYSTEM,
        conditions=None,
        user_id=user_id,
        creation_date=valid_from,
        revocation_date=None,
    )


def is_data_steward_claim(claim: Claim) -> bool:
    """Check whether the given claim asserts a data steward role."""
    if not is_internal_claim(claim, VisaType.GHGA_ROLE):
        return False
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return False
    role_name = visa_value.split("@", 1)[0]
    return role_name == DATA_STEWARD_ROLE


# Controlled Access Claims


def create_controlled_access_claim(
    user_id: str, dataset_id: str, valid_from: DateTimeUTC, valid_until: DateTimeUTC
) -> ClaimFullCreation:
    """Create a claim for a controlled access grant."""
    creation_date = now_as_utc()
    return ClaimFullCreation(
        visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
        visa_value=parse_obj_as(HttpUrl, DATASET_PREFIX + dataset_id),
        assertion_date=creation_date,
        valid_from=valid_from,
        valid_until=valid_until,
        source=INTERNAL_SOURCE,
        sub_source=None,
        asserted_by=AuthorityLevel.DAC,
        conditions=None,
        user_id=user_id,
        creation_date=creation_date,
        revocation_date=None,
    )


def get_dataset_for_value(value: str) -> Optional[str]:
    """Return the dataset ID if the given value is a Visa URL Claim for a dataset."""
    if not value.startswith(DATASET_PREFIX):
        return None
    return value.removeprefix(DATASET_PREFIX)


def has_download_access_for_dataset(claim: Claim, dataset_id: str) -> bool:
    """Check whether the given claim gives download access to the given dataset."""
    if not is_internal_claim(claim, VisaType.CONTROLLED_ACCESS_GRANTS):
        return False
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return False
    return get_dataset_for_value(visa_value) == dataset_id


def dataset_id_for_download_access(claim: Claim) -> Optional[str]:
    """Return dataset ID if the given claim gives download access to a dataset."""
    if not is_internal_claim(claim, VisaType.CONTROLLED_ACCESS_GRANTS):
        return None
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return None
    return get_dataset_for_value(visa_value)
