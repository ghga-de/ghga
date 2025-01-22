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

"""Database version checking & migration before startup"""

from ifrs.config import Config
from ifrs.migration_logic import MigrationManager, MigrationMap
from ifrs.migration_logic.ifrs_migrations import V2Migration

MIGRATION_MAP: MigrationMap = {2: V2Migration}
DB_TARGET_VERSION = 2


async def run_db_migrations(
    *,
    config: Config,
    target_version: int = DB_TARGET_VERSION,
):
    """Check if the database is up to date and attempt to migrate the data if not.

    The service must not start until this function is successful.

    Args
    - `config`: Config containing db connection str and lock/db versioning collections
    - `target_version`: Which version the db needs to be at for this version of the service

    `target_version` can be specified to aid in testing.
    """
    async with MigrationManager(
        config=config,
        target_version=target_version,
        migration_map=MIGRATION_MAP,
    ) as mm:
        await mm.migrate_or_wait()
