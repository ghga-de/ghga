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

"""Manage request and response headers"""

import json
from collections.abc import Callable

from fastapi import Request, Response, status

from ..core.session_store import Session

__all__ = ["get_bearer_token", "session_to_header", "pass_auth_response"]


def get_bearer_token(*header_values: str | None) -> str | None:
    """Extract the bearer token from the authorization header.

    Multiple possible authorization header values can be passed,
    in case one of them is used for Basic authentication.

    Return None if no bearer token was found in one of the header values.
    """
    for header_value in header_values:
        if header_value and header_value.startswith("Bearer "):
            return header_value.removeprefix("Bearer ")
    return None


def session_to_header(
    session: Session, timeouts: Callable[[Session], tuple[int, int]] | None = None
) -> str:
    """Serialize a session to a response header value to be used by the frontend."""
    session_dict: dict[str, str | int] = {
        "ext_id": session.ext_id,
        "name": session.user_name,
        "email": session.user_email,
        "state": session.state.value,
        "csrf": session.csrf_token,
    }
    if session.user_id:
        session_dict["id"] = session.user_id
    if session.user_title:
        session_dict["title"] = session.user_title
    if session.role:
        session_dict["role"] = session.role
    if timeouts:
        timeout_soft, timeout_hard = timeouts(session)
        session_dict["timeout"] = timeout_soft
        session_dict["extends"] = timeout_hard
    return json.dumps(session_dict, ensure_ascii=False, separators=(",", ":"))


def pass_auth_response(request: Request, authorization: str | None = None) -> Response:
    """Create a response for ExtAuth that signals that the request is authorized.

    The Authorization header is set as specified.

    All other headers that exist in the request and that should not be forwarded
    to the backend, because they are only relevant for the auth adapter, are emptied.
    """
    headers: dict[str, str] = {}
    for header in "Authorization", "X-Authorization", "Cookie", "X-CSRF-Token":
        value = request.headers.get(header)
        if value:
            headers[header] = ""
    if authorization:
        headers["Authorization"] = authorization
    return Response(status_code=status.HTTP_200_OK, headers=headers)
