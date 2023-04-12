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

from typing import Callable, Optional

from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc

from ....config import CONFIG
from ..models.dto import AuthorityLevel, Claim, VisaType

__all__ = [
    "dataset_id_for_download_access",
    "is_valid_claim",
    "is_internal_claim",
    "is_data_steward_claim",
    "get_dataset_for_value",
    "has_download_access_for_dataset",
]


INTERNAL_SOURCE = CONFIG.organization_url
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


def is_data_steward_claim(claim: Claim) -> bool:
    """Check whether the given claim asserts a data steward role."""
    if not is_internal_claim(claim, VisaType.GHGA_ROLE):
        return False
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return False
    role_name = visa_value.split("@", 1)[0]
    return role_name == DATA_STEWARD_ROLE


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
