# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from uuid import UUID

from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from ...config import CONFIG
from ..models.claims import AuthorityLevel, Claim, VisaType

__all__ = [
    "Role",
    "box_id_for_upload_access",
    "create_controlled_access_claim",
    "create_controlled_access_filter",
    "create_internal_role_claim",
    "create_upload_access_claim",
    "create_upload_access_filter",
    "dataset_id_for_download_access",
    "get_box_for_value",
    "get_dataset_for_value",
    "get_role_from_claim",
    "has_download_access_for_dataset",
    "has_upload_access_for_box",
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
UPLOAD_PREFIX = str(INTERNAL_SOURCE).rstrip("/") + "/uploads/"


def is_valid_claim(
    claim: Claim, now: Callable[[], UTCDatetime] = now_utc_ms_prec
) -> bool:
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
    user_id: UUID4, role: Role, iva_id: UUID4 | None = None, valid_days=365
) -> Claim:
    """Create a claim for a data steward with the given IVA."""
    valid_from = now_utc_ms_prec()
    valid_until = now_utc_ms_prec() + timedelta(days=valid_days)
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
    user_id: UUID4,
    iva_id: UUID4,
    dataset_id: str,
    valid_from: UTCDatetime,
    valid_until: UTCDatetime,
) -> Claim:
    """Create a claim for a controlled access grant."""
    creation_date = now_utc_ms_prec()
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


def create_controlled_access_filter(
    *,
    user_id: UUID4 | None = None,
    iva_id: UUID4 | None = None,
    dataset_id: str | None = None,
) -> dict[str, UUID4 | str]:
    """Create a mapping for filtering controlled access grants.

    If a user, IVA or dataset ID is given, filter values will be set accordingly.
    """
    mapping: dict[str, UUID4 | str] = {
        "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS.value,
        "source": str(INTERNAL_SOURCE).rstrip("/"),
    }
    if user_id:
        mapping["user_id"] = user_id
    if iva_id:
        mapping["iva_id"] = iva_id
    if dataset_id:
        mapping["visa_value"] = DATASET_PREFIX + dataset_id
    return mapping


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


# Upload Access Claims


def create_upload_access_claim(
    user_id: UUID4,
    iva_id: UUID4,
    box_id: UUID4,
    valid_from: UTCDatetime,
    valid_until: UTCDatetime,
) -> Claim:
    """Create a claim for an upload access grant."""
    creation_date = now_utc_ms_prec()
    return Claim(
        visa_type=VisaType.GHGA_UPLOAD,
        visa_value=UPLOAD_PREFIX + str(box_id),
        assertion_date=creation_date,
        valid_from=valid_from,
        valid_until=valid_until,
        source=INTERNAL_SOURCE,
        sub_source=None,
        asserted_by=AuthorityLevel.SYSTEM,
        conditions=None,
        user_id=user_id,
        iva_id=iva_id,
        creation_date=creation_date,
        revocation_date=None,
    )


def create_upload_access_filter(
    *,
    user_id: UUID4 | None = None,
    iva_id: UUID4 | None = None,
    box_id: UUID4 | None = None,
) -> dict[str, UUID4 | str]:
    """Create a mapping for filtering upload access grants.

    If a user, IVA or box ID is given, filter values will be set accordingly.
    """
    mapping: dict[str, UUID4 | str] = {
        "visa_type": VisaType.GHGA_UPLOAD.value,
        "source": str(INTERNAL_SOURCE).rstrip("/"),
    }
    if user_id:
        mapping["user_id"] = user_id
    if iva_id:
        mapping["iva_id"] = iva_id
    if box_id:
        mapping["visa_value"] = UPLOAD_PREFIX + str(box_id)
    return mapping


def get_box_for_value(value: str) -> UUID4 | None:
    """Return the box ID if the given value is a Visa URL Claim for an upload box."""
    if not value.startswith(UPLOAD_PREFIX):
        return None
    return UUID(value.removeprefix(UPLOAD_PREFIX))


def has_upload_access_for_box(claim: Claim, box_id: UUID4) -> bool:
    """Check whether the given claim gives upload access to the given box."""
    if not is_internal_claim(claim, VisaType.GHGA_UPLOAD):
        return False
    visa_value = claim.visa_value
    return get_box_for_value(str(visa_value)) == box_id


def box_id_for_upload_access(claim: Claim) -> UUID4 | None:
    """Return box ID if the given claim gives upload access to a box."""
    if not is_internal_claim(claim, VisaType.GHGA_UPLOAD):
        return None
    visa_value = claim.visa_value
    return get_box_for_value(str(visa_value))
