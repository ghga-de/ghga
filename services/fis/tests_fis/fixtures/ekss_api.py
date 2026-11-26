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

__all__ = ["DEPOSITED_SECRET_ID", "EkssApiMock"]

from fastapi import status

from fis.adapters.outbound.secrets import (
    DELETION_PATH,
    DEPOSIT_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond

DEPOSITED_SECRET_ID = "some-secret-id"


class EkssApiMock(MockApi):
    """A mock of the EKSS API endpoints the FIS calls, succeeding by default."""

    def __init__(self, *, config: SecretsClientConfig) -> None:
        super().__init__(str(config.ekss_api_url))
        self.on_deposit_secret: ResponseHandler = respond(
            status.HTTP_201_CREATED, json={"secret_id": DEPOSITED_SECRET_ID}
        )
        self.on_delete_secret: ResponseHandler = respond(status.HTTP_204_NO_CONTENT)
        self.route("POST", DEPOSIT_PATH, "on_deposit_secret")
        self.route("DELETE", DELETION_PATH, "on_delete_secret")
