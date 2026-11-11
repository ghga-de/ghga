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

"""A mock of the EKSS API, built on the service commons `MockApi`."""

__all__ = ["ENVELOPE", "SECRET_ID", "EkssApiMock", "secret_not_found"]

from fastapi import status

from dcs.adapters.outbound.http.secrets import (
    DELETION_PATH,
    ENVELOPE_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond

SECRET_ID = "some-secret"

ENVELOPE = (
    "pfAcB7o2lz0075VTpb6b5PCdfWnPofyZ62RYxQ6gZflUoCuwSt//R2N6QCWTnn7wV/oU8syQBCgB/1KTqz77v"
    + "8jBF73IyszJzVezDokPe8AJIEFG18luo/ZRI9mDSEI/GFy2EtNdflqW+CBSgUEWiQjkRAwS3V+dVeFsVQ=="
)


def secret_not_found() -> ResponseHandler:
    """Make a handler answering with the httpyexpect body for an unknown secret."""
    return respond(
        status.HTTP_404_NOT_FOUND,
        json={
            "exception_id": "secretNotFoundError",
            "description": "The secret for the given id was not found.",
            "data": {},
        },
    )


class EkssApiMock(MockApi):
    """A mock of the EKSS API endpoints the DCS calls, succeeding by default."""

    def __init__(self, *, config: SecretsClientConfig) -> None:
        super().__init__(config.ekss_base_url)
        self.on_get_envelope: ResponseHandler = respond(
            status.HTTP_200_OK, json={"content": ENVELOPE}
        )
        self.on_delete_secret: ResponseHandler = respond(status.HTTP_204_NO_CONTENT)
        self.route("GET", ENVELOPE_PATH, "on_get_envelope")
        self.route("DELETE", DELETION_PATH, "on_delete_secret")
