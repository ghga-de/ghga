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

"""Shared fixtures for the auth-km-jobs tests.

Upstream these tests assumed Vault and MongoDB were already running externally (at
localhost). Here we spin them up as ephemeral testcontainers via hexkit's provider
fixtures — matching the rest of the monorepo — and point the auth_km_jobs module-level
`config` singletons at them so the code under test talks to the containers.
"""

import auth_km_jobs.jwks
import auth_km_jobs.totp
import auth_km_jobs.vault
import pytest
from hexkit.providers.mongodb.testutils import (
    mongodb_container_fixture,  # noqa: F401
    mongodb_fixture,  # noqa: F401
)
from hexkit.providers.vault.testutils import (
    VAULT_TEST_ROOT_TOKEN,
    vault_container_fixture,  # noqa: F401
    vault_fixture,  # noqa: F401
)

from auth_km_jobs.config import Config


@pytest.fixture(name="config")
def config_fixture(request, vault, mongodb, monkeypatch):
    """Build a Config pointed at the ephemeral Vault + MongoDB containers and inject it
    into the auth_km_jobs module singletons (and the requesting test module).

    The code under test reads a module-level ``config`` global at call time, so replacing
    that global redirects every Vault/Mongo access to the containers. Token auth with the
    dev-mode root token is used (the tool's default auth path when no kube role is set).
    """
    cfg = Config(
        vault_addr=vault.config.vault_url,
        token=VAULT_TEST_ROOT_TOKEN,
        mount_point=vault.config.vault_secrets_mount_point,
        ssl_verify=False,
        mongo_dsn=str(mongodb.config.mongo_dsn.get_secret_value()),
        db_name=mongodb.config.db_name,
    )
    for module in (
        auth_km_jobs.vault,
        auth_km_jobs.totp,
        auth_km_jobs.jwks,
        request.module,
    ):
        if hasattr(module, "config"):
            monkeypatch.setattr(module, "config", cfg)
    return cfg
