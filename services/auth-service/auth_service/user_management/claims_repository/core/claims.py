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

from typing import Callable

from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc

from ....config import CONFIG
from ..models.dto import AuthorityLevel, Claim, VisaType

__all__ = ["is_valid_claim", "is_data_steward_claim"]


INTERNAL_SOURCE = CONFIG.organization_url
DATA_STEWARD_ROLE = "data_steward"


def is_valid_claim(claim: Claim, now: Callable[[], DateTimeUTC] = now_as_utc) -> bool:
    """Check whether the given claim is currently valid."""
    return not claim.revocation_date and claim.valid_from <= now() <= claim.valid_until


def is_data_steward_claim(claim: Claim) -> bool:
    """Check whether the given claim asserts a data steward role."""
    if (
        claim.visa_type != VisaType.GHGA_ROLE
        or claim.source != INTERNAL_SOURCE
        or not claim.asserted_by
        or claim.asserted_by == AuthorityLevel.SELF
    ):
        return False
    visa_value = claim.visa_value
    if not isinstance(visa_value, str):
        return False
    role_name = visa_value.split("@", 1)[0]
    return role_name == DATA_STEWARD_ROLE
