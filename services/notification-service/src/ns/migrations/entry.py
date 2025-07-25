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

"""Module containing controller function for DB migrations"""

from hexkit.providers.mongodb.migrations import (
    MigrationConfig,
    MigrationManager,
    MigrationMap,
)

from ns.migrations.definitions import V2Migration

MIGRATION_MAP = {2: V2Migration}


async def run_db_migrations(
    *,
    config: MigrationConfig,
    target_version: int,
    migration_map: MigrationMap | None = None,
):
    """Run all migrations.

    Args
    - `config`: Config containing mongo_dsn string and DB versioning collection name
    - `target_version`: Which version the db needs to be at for this version of the service
    - `migration_map`: Mapping of version to migration definition. Defaults to `MIGRATION_MAP`.

    `migration_map` can be specified for testing, but may be left unspecified for production.
    """
    migration_map = migration_map or MIGRATION_MAP

    async with MigrationManager(
        config=config,
        target_version=target_version,
        migration_map=MIGRATION_MAP,
    ) as mm:
        await mm.migrate_or_wait()
