# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Provides client side functionality for interaction with HashiCorp Vault"""

import base64
import logging
from uuid import uuid4

import hvac
import hvac.exceptions
from hvac.api.auth_methods import Kubernetes
from opentelemetry import trace

from ekss.adapters.outbound.vault import exceptions
from ekss.config import VaultConfig

log = logging.getLogger(__name__)
tracer = trace.get_tracer("ekss")


class VaultAdapter:
    """Adapter wrapping hvac.Client"""

    def __init__(self, config: VaultConfig):
        """Initialized approle based client and login"""
        self._client = hvac.Client(url=config.vault_url, verify=config.vault_verify)
        self._path = config.vault_path
        self._auth_mount_point = config.vault_auth_mount_point
        self._secrets_mount_point = config.vault_secrets_mount_point

        self._kube_role = config.vault_kube_role
        if self._kube_role:
            # use kube role and service account token
            self._kube_role = self._kube_role
            self._kube_adapter = Kubernetes(self._client.adapter)
            self._service_account_token_path = config.service_account_token_path
        elif config.vault_role_id and config.vault_secret_id:
            # use role and secret ID instead
            self._role_id = config.vault_role_id.get_secret_value()
            self._secret_id = config.vault_secret_id.get_secret_value()
        else:
            raise ValueError(
                "There is no way to log in to vault:\n"
                + "Neither kube role nor both role and secret ID were provided."
            )

    def _check_auth(self):
        """Check if authentication timed out and re-authenticate if needed"""
        if not self._client.is_authenticated():
            self._login()

    def _login(self):
        """Log in using Kubernetes Auth or AppRole"""
        if self._kube_role:
            with self._service_account_token_path.open() as token_file:
                jwt = token_file.read()
            if self._auth_mount_point:
                self._kube_adapter.login(
                    role=self._kube_role, jwt=jwt, mount_point=self._auth_mount_point
                )
            else:
                self._kube_adapter.login(role=self._kube_role, jwt=jwt)

        elif self._auth_mount_point:
            self._client.auth.approle.login(
                role_id=self._role_id,
                secret_id=self._secret_id,
                mount_point=self._auth_mount_point,
            )
        else:
            self._client.auth.approle.login(
                role_id=self._role_id, secret_id=self._secret_id
            )

    @tracer.start_as_current_span("VaultAdapter.store_secret")
    def store_secret(self, *, secret: bytes) -> str:
        """
        Store a secret under a subpath of the given prefix.
        Generates a UUID4 as key, uses it for the subpath and returns it.
        """
        value = base64.b64encode(secret).decode("utf-8")
        key = str(uuid4())

        self._check_auth()
        path = f"{self._path}/{key}"

        try:
            # set cas to 0 as we only want a static secret
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret={key: value},
                cas=0,
                mount_point=self._secrets_mount_point,
            )
        except hvac.exceptions.InvalidRequest as exc:
            log.debug("Invalid request error when storing secret at %s: %s", path, exc)
            raise exceptions.SecretInsertionError() from exc
        return key

    @tracer.start_as_current_span("VaultAdapter.get_secret")
    def get_secret(self, *, key: str) -> bytes:
        """
        Retrieve a secret at the subpath of the given prefix denoted by key.
        Key should be a UUID4 returned by store_secret on insertion
        """
        self._check_auth()
        path = f"{self._path}/{key}"

        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                raise_on_deleted_version=True,
                mount_point=self._secrets_mount_point,
            )
        except hvac.exceptions.InvalidPath as exc:
            log.debug("Invalid path error when fetching secret at %s: %s", path, exc)
            raise exceptions.SecretRetrievalError() from exc

        secret = response["data"]["data"][key]
        return base64.b64decode(secret)

    @tracer.start_as_current_span("VaultAdapter.delete_secret")
    def delete_secret(self, *, key: str) -> None:
        """Delete a secret"""
        self._check_auth()
        path = f"{self._path}/{key}"

        try:
            self._client.secrets.kv.v2.read_secret_version(
                path=path,
                raise_on_deleted_version=True,
                mount_point=self._secrets_mount_point,
            )
        except hvac.exceptions.InvalidPath as exc:
            log.debug("Invalid path error when deleting secret at %s: %s", path, exc)
            raise exceptions.SecretRetrievalError() from exc

        response = self._client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path,
            mount_point=self._secrets_mount_point,
        )

        # Check the response status
        status_code = response.status_code
        if status_code != 204:
            log.debug(
                "Unexpected status code %d when deleting secret at %s",
                status_code,
                path,
            )
            raise exceptions.SecretDeletionError()
