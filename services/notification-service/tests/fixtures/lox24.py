# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""A mock of the Lox24 SMS gateway, based on the service commons `ApiMock`."""

import json

import pytest
from httpx2 import Request, Response
from jsonschema_path import SchemaPath
from openapi_core.contrib.requests import RequestsOpenAPIRequest
from openapi_core.validation.request.validators import V30RequestValidator
from requests import PreparedRequest
from requests import Request as RequestsRequest

from ghga_service_commons.api.mock_api import ApiMock, endpoint
from tests.fixtures.config import get_config
from tests.fixtures.utils import BASE_DIR

LOX24_OPENAPI_SPEC = BASE_DIR / "lox24_openapi.json"

SEND_SMS_PATH = "/sms"

SENT_SMS_UUID = "00000000-0000-0000-0000-000000000000"


class Lox24Mock(ApiMock):
    """Mock of the Lox24 SMS gateway that records every request it receives.

    `status_code` determines what the send-SMS endpoint responds with, and
    `expected_json` the payload it accepts. Both can be changed at any point before
    the request under test is made.
    """

    on_send_sms = endpoint("POST", SEND_SMS_PATH)

    def __init__(self, *, base_url: str, auth_token: str, auth_token_header: str):
        """Serve the SMS gateway at `base_url`, expecting the given auth token."""
        super().__init__(base_url=base_url)
        self.status_code: int = 201
        self.expected_json: dict[str, str] | None = None
        self._auth_token = auth_token
        self._auth_token_header = auth_token_header
        self.on_send_sms = self.send_sms

    def send_sms(self, request: Request, **path_variables: str) -> Response:
        """Record the request and respond with the configured status code."""
        self._match_request(request)
        return Response(status_code=self.status_code, json={"uuid": SENT_SMS_UUID})

    def _match_request(self, request: Request):
        """Raise unless the request carries the expected auth token and payload.

        An unexpected request is rejected rather than answered, because any response
        would be indistinguishable from the one configured for the test at hand.
        """
        token = request.headers.get(self._auth_token_header)
        if token != self._auth_token:
            raise AssertionError(
                f"Expected the {self._auth_token_header} header to be"
                + f" {self._auth_token!r}, got {token!r}"
            )
        if self.expected_json is not None:
            payload = json.loads(request.content)
            if payload != self.expected_json:
                raise AssertionError(
                    f"Expected the payload to be {self.expected_json}, got {payload}"
                )

    def validate_requests(self):
        """Check all recorded requests against the Lox24 OpenAPI spec."""
        with open(LOX24_OPENAPI_SPEC) as spec_file:
            spec = SchemaPath.from_dict(json.load(spec_file))
        request_validator = V30RequestValidator(spec)

        for request in self.requests:
            request_validator.validate(
                RequestsOpenAPIRequest(_to_prepared_request(request))
            )


def _to_prepared_request(request: Request) -> PreparedRequest:
    """Convert an httpx2 request, since openapi-core can only validate requests
    from the `requests` library.
    """
    return RequestsRequest(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers),
        data=request.content or request.stream or None,  # type: ignore
    ).prepare()


@pytest.fixture(name="lox24")
def lox24_fixture() -> Lox24Mock:
    """Provide a mocked Lox24 SMS gateway for a single test case."""
    config = get_config()
    return Lox24Mock(
        base_url=str(config.lox24_base_url),
        auth_token=config.lox24_token.get_secret_value(),
        auth_token_header=config.lox24_auth_token_header,
    )
