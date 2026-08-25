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

"""A mock of the EKSS API, built on the service commons `ApiMock`."""

__all__ = [
    "DEPOSITED_SECRET_ID",
    "EkssApiMock",
]

from fastapi import status

from fis.adapters.outbound.secrets import (
    DELETION_PATH,
    DEPOSIT_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.api.mock_api import ApiMock, endpoint, respond

DEPOSITED_SECRET_ID = "some-secret-id"


class EkssApiMock(ApiMock):
    """A mock of the EKSS API endpoints that the FIS talks to.

    Each endpoint answers with the handler assigned to `on_deposit_secret` or
    `on_delete_secret`. Tests can swap those out with `respond(...)`,
    `fail_to_connect(...)` or any other callable taking the request. Every request
    that reaches the mock is recorded in `requests`.
    """

    on_deposit_secret = endpoint(
        "POST",
        DEPOSIT_PATH,
        respond(status.HTTP_201_CREATED, json={"secret_id": DEPOSITED_SECRET_ID}),
    )
    on_delete_secret = endpoint(
        "DELETE", DELETION_PATH, respond(status.HTTP_204_NO_CONTENT)
    )

    def __init__(self, *, config: SecretsClientConfig) -> None:
        """Serve the EKSS API where the given config expects it."""
        super().__init__(base_url=str(config.ekss_api_url))
