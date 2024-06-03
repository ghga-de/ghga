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
"""HashiCorp vault fixture for texting"""

import time
from collections.abc import Generator
from dataclasses import dataclass

import hvac
import pytest
from testcontainers.general import DockerContainer

from ekss.adapters.inbound.fastapi_.deps import VaultConfig
from ekss.adapters.outbound.vault.client import VaultAdapter

VAULT_URL = "http://0.0.0.0:8200"
VAULT_NAMESPACE = "vault"
VAULT_TOKEN = "dev-token"
VAULT_PORT = 8200


@dataclass
class VaultFixture:
    """Contains initialized vault client"""

    adapter: VaultAdapter
    config: VaultConfig


@pytest.fixture
def vault_fixture() -> Generator[VaultFixture, None, None]:
    """Generate preconfigured test container"""
    vault_container = (
        DockerContainer(image="hashicorp/vault:1.12")
        .with_exposed_ports(VAULT_PORT)
        .with_env("VAULT_ADDR", VAULT_URL)
        .with_env("VAULT_DEV_ROOT_TOKEN_ID", VAULT_TOKEN)
    )
    with vault_container:
        host = vault_container.get_container_host_ip()
        port = vault_container.get_exposed_port(VAULT_PORT)
        role_id, secret_id = configure_vault(host=host, port=int(port))
        config = VaultConfig(
            vault_url=f"http://{host}:{port}",
            vault_role_id=role_id,
            vault_secret_id=secret_id,
            vault_verify=True,
            vault_path="ekss",
        )
        vault_adapter = VaultAdapter(config=config)
        # client needs some time after creation
        time.sleep(2)
        yield VaultFixture(adapter=vault_adapter, config=config)


def configure_vault(*, host: str, port: int):
    """Configure vault using direct interaction with hvac.Client"""
    client = hvac.Client(url=f"http://{host}:{port}", token=VAULT_TOKEN)
    # client needs some time after creation
    time.sleep(2)

    # enable authentication with role_id/secret_id
    client.sys.enable_auth_method(
        method_type="approle",
    )

    # create access policy to bind to role
    ekss_policy = """
    path "secret/data/ekss/*" {
        capabilities = ["read", "create"]
    }
    path "secret/metadata/ekss/*" {
        capabilities = ["delete"]
    }
    """

    # inject policy
    client.sys.create_or_update_policy(
        name="ekss",
        policy=ekss_policy,
    )

    role_name = "test_role"
    # create role and bind policy
    response = client.auth.approle.create_or_update_approle(
        role_name=role_name,
        token_policies=["ekss"],
        token_type="service",
    )

    # retrieve role_id
    response = client.auth.approle.read_role_id(role_name=role_name)
    role_id = response["data"]["role_id"]

    # retrieve secret_id
    response = client.auth.approle.generate_secret_id(
        role_name=role_name,
    )
    secret_id = response["data"]["secret_id"]

    # log out root token client
    client.logout()

    return role_id, secret_id
