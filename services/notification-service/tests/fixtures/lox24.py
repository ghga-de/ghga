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
"""A mock of the Lox24 SMS gateway, based on the service commons `MockApi`."""

import json

import pytest
from httpx2 import Request
from jsonschema_path import SchemaPath
from openapi_core.contrib.requests import RequestsOpenAPIRequest
from openapi_core.validation.request.validators import V30RequestValidator
from requests import PreparedRequest
from requests import Request as RequestsRequest

from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond
from tests.fixtures.config import get_config
from tests.fixtures.utils import BASE_DIR

LOX24_OPENAPI_SPEC = BASE_DIR / "lox24_openapi.json"

SEND_SMS_PATH = "/sms"

SENT_SMS_UUID = "00000000-0000-0000-0000-000000000000"


class Lox24Mock(MockApi):
    """A mock of the Lox24 SMS gateway, accepting every SMS by default."""

    def __init__(self, *, base_url: str, auth_token: str, auth_token_header: str):
        super().__init__(base_url)
        self._auth_token = auth_token
        self._auth_token_header = auth_token_header
        self.on_send_sms: ResponseHandler = respond(201, json={"uuid": SENT_SMS_UUID})
        self.route("POST", SEND_SMS_PATH, "on_send_sms")

    def validate_requests(self):
        """Check every request's auth token and its fit with the Lox24 OpenAPI spec."""
        with open(LOX24_OPENAPI_SPEC) as spec_file:
            spec = SchemaPath.from_dict(json.load(spec_file))
        request_validator = V30RequestValidator(spec)

        for request in self.requests:
            token = request.headers.get(self._auth_token_header)
            assert token == self._auth_token, (
                f"Expected the {self._auth_token_header} header to be"
                + f" {self._auth_token!r}, got {token!r}"
            )
            request_validator.validate(
                RequestsOpenAPIRequest(_to_prepared_request(request))
            )


def _to_prepared_request(request: Request) -> PreparedRequest:
    """Convert an httpx2 request, as openapi-core validates `requests` ones only."""
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
