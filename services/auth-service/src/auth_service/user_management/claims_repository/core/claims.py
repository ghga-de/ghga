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

"""Definitions and helper functions for validating user claims."""

from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc

from ....config import CONFIG
from ..models.claims import AuthorityLevel, Claim, VisaType

__all__ = [
    "Role",
    "create_controlled_access_claim",
    "create_controlled_access_filter",
    "create_internal_role_claim",
    "dataset_id_for_download_access",
    "get_dataset_for_value",
    "get_role_from_claim",
    "has_download_access_for_dataset",
    "is_internal_claim",
    "is_valid_claim",
]


INTERNAL_SOURCE = CONFIG.organization_url
INTERNAL_DOMAIN = INTERNAL_SOURCE.host


class Role(StrEnum):
    """All supported role names for internal roles."""

    ADMIN = "admin"
    DATA_STEWARD = "data_steward"


DATASET_PREFIX = str(INTERNAL_SOURCE).rstrip("/") + "/datasets/"


def is_valid_claim(claim: Claim, now: Callable[[], UTCDatetime] = now_as_utc) -> bool:
    """Check whether the given claim is currently valid.

    This function does not check the existence and status of an associated IVA.
    """
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


# Internal Role Claims


def create_internal_role_claim(
    user_id: str, role: Role, iva_id: str | None = None, valid_days=365
) -> Claim:
    """Create a claim for a data steward with the given IVA."""
    valid_from = now_as_utc()
    valid_until = now_as_utc() + timedelta(days=valid_days)
    return Claim(
        visa_type=VisaType.GHGA_ROLE,
        visa_value=f"{role}@{INTERNAL_DOMAIN}",
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
        iva_id=iva_id,
    )


def get_role_from_claim(claim: Claim) -> Role | None:
    """Get the internal role from a claim

    The function checks whether the claim is a supported internal role claim
    and returns the corresponding role if that is the case and None otherwise.
    Note that this function does not check the validity of the claim
    nor does it check the existence and status of an associated IVA.
    """
    if not is_internal_claim(claim, VisaType.GHGA_ROLE):
        return None
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return None
    role_name = visa_value.split("@", 1)[0]
    if role_name not in Role:
        return None
    return Role(role_name)


# Controlled Access Claims


def create_controlled_access_claim(
    user_id: str,
    iva_id: str,
    dataset_id: str,
    valid_from: UTCDatetime,
    valid_until: UTCDatetime,
) -> Claim:
    """Create a claim for a controlled access grant."""
    creation_date = now_as_utc()
    return Claim(
        visa_type=VisaType.CONTROLLED_ACCESS_GRANTS,
        visa_value=DATASET_PREFIX + dataset_id,
        assertion_date=creation_date,
        valid_from=valid_from,
        valid_until=valid_until,
        source=INTERNAL_SOURCE,
        sub_source=None,
        asserted_by=AuthorityLevel.DAC,
        conditions=None,
        user_id=user_id,
        iva_id=iva_id,
        creation_date=creation_date,
        revocation_date=None,
    )


def create_controlled_access_filter(dataset_id: str) -> dict[str, str]:
    """Create a mapping for filtering controlled access grants for a given dataset."""
    return {
        "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS.value,
        "visa_value": DATASET_PREFIX + dataset_id,
        "source": str(INTERNAL_SOURCE).rstrip("/"),
    }


def get_dataset_for_value(value: str) -> str | None:
    """Return the dataset ID if the given value is a Visa URL Claim for a dataset."""
    if not value.startswith(DATASET_PREFIX):
        return None
    return value.removeprefix(DATASET_PREFIX)


def has_download_access_for_dataset(claim: Claim, dataset_id: str) -> bool:
    """Check whether the given claim gives download access to the given dataset."""
    if not is_internal_claim(claim, VisaType.CONTROLLED_ACCESS_GRANTS):
        return False
    visa_value = claim.visa_value
    return get_dataset_for_value(str(visa_value)) == dataset_id


def dataset_id_for_download_access(claim: Claim) -> str | None:
    """Return dataset ID if the given claim gives download access to a dataset."""
    if not is_internal_claim(claim, VisaType.CONTROLLED_ACCESS_GRANTS):
        return None
    visa_value = claim.visa_value
    return get_dataset_for_value(str(visa_value))
