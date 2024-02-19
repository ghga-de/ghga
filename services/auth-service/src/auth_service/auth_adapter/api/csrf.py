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

"""Cross-site request forgery (CSRF) protection."""

from typing import Optional

from fastapi import HTTPException, status

from ..core.session_store import Session

__all__ = ["check_csrf"]

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def check_csrf(
    method: str, csrf_token: Optional[str], session: Optional[Session]
) -> None:
    """Check the CSRF token.

    Raises an unauthorized exception if the CSRF token is missing or invalid.
    """
    if (
        session
        and method in WRITE_METHODS
        and (not csrf_token or csrf_token != session.csrf_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing CSRF token",
        )
