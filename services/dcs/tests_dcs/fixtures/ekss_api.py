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
"""A mock of the EKSS API, built on `MockedApi`."""

__all__ = [
    "ENVELOPE",
    "SECRET_ID",
    "EkssApiMock",
    "secret_not_found",
]

from fastapi import status

from dcs.adapters.outbound.http.secrets import (
    DELETION_PATH,
    ENVELOPE_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.api.mock_api import (
    MockedApi,
    ResponseHandler,
    endpoint,
    httpyexpect_body,
    respond,
)

SECRET_ID = "some-secret"

ENVELOPE = (
    "pfAcB7o2lz0075VTpb6b5PCdfWnPofyZ62RYxQ6gZflUoCuwSt//R2N6QCWTnn7wV/oU8syQBCgB/1KTqz77v"
    + "8jBF73IyszJzVezDokPe8AJIEFG18luo/ZRI9mDSEI/GFy2EtNdflqW+CBSgUEWiQjkRAwS3V+dVeFsVQ=="
)


def secret_not_found() -> ResponseHandler:
    """Make a handler answering with the httpyexpect body for an unknown secret."""
    return respond(
        status.HTTP_404_NOT_FOUND,
        json=httpyexpect_body(
            "secretNotFoundError", "The secret for the given id was not found."
        ),
    )


class EkssApiMock(MockedApi):
    """A mock of the EKSS API endpoints that the DCS talks to.

    Each endpoint answers with the handler assigned to `on_get_envelope` or
    `on_delete_secret`. Tests can swap those out with `respond(...)`,
    `fail_to_connect(...)`, `secret_not_found()` or any other callable taking the
    request. Every request that reaches the mock is recorded in `requests`.

    The transport returned by `as_transport()` answers *every* request, so a test
    using it cannot accidentally reach the network - a URL no endpoint serves is
    refused rather than being sent out.
    """

    on_get_envelope = endpoint(
        "GET", ENVELOPE_PATH, respond(status.HTTP_200_OK, json={"content": ENVELOPE})
    )
    on_delete_secret = endpoint(
        "DELETE", DELETION_PATH, respond(status.HTTP_204_NO_CONTENT)
    )

    def __init__(self, *, config: SecretsClientConfig) -> None:
        """Serve the EKSS API where the config says it is."""
        super().__init__(str(config.ekss_base_url))
