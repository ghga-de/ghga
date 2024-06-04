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

"""HTTP calls to other service APIs happen here"""

import base64

import httpx

from dcs.adapters.outbound.http import exceptions
from dcs.adapters.outbound.http.exception_translation import ResponseExceptionTranslator


def get_envelope_from_ekss(
    *, secret_id: str, receiver_public_key: str, api_base: str
) -> str:
    """Calls EKSS to get an envelope for an encrypted file, using the receivers
    public key as well as the id of the file secret.
    """
    receiver_public_key_base64 = base64.urlsafe_b64encode(
        base64.b64decode(receiver_public_key)
    ).decode()
    api_url = f"{
        api_base}/secrets/{secret_id}/envelopes/{receiver_public_key_base64}"
    try:
        response = httpx.get(url=api_url, timeout=60)
    except httpx.RequestError as request_error:
        raise exceptions.RequestFailedError(url=api_base) from request_error

    status_code = response.status_code
    # implement httpyexpect error conversion
    if status_code != 200:
        spec: dict[int, object] = {
            404: {
                "secretNotFoundError": lambda: exceptions.SecretNotFoundError(
                    secret_id=secret_id
                )
            },
        }
        ResponseExceptionTranslator(spec=spec).handle(response=response)
        raise exceptions.BadResponseCodeError(url=api_base, response_code=status_code)

    body = response.json()
    content = body["content"]

    return content


def delete_secret_from_ekss(*, secret_id: str, api_base: str) -> None:
    """Calls EKSS to delete a file secret"""
    api_url = f"{api_base}/secrets/{secret_id}"

    try:
        response = httpx.delete(url=api_url, timeout=60)
    except httpx.RequestError as request_error:
        raise exceptions.RequestFailedError(url=api_base) from request_error

    status_code = response.status_code

    # implement httpyexpect error conversion
    if status_code != 204:
        spec: dict[int, object] = {
            404: {
                "secretNotFoundError": lambda: exceptions.SecretNotFoundError(
                    secret_id=secret_id
                )
            },
        }
        ResponseExceptionTranslator(spec=spec).handle(response=response)
        raise exceptions.BadResponseCodeError(url=api_base, response_code=status_code)
