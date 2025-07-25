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

"""Database migration logic for NS"""

from hexkit.providers.mongodb.migrations import MigrationDefinition


class V2Migration(MigrationDefinition):
    """Drop the `notification_records` collection after migrating to hexkit v6.

    Reason: The collection itself is still used, but the prior data is no longer valid.
    The old format stored a hash sum + sent flag. The new version stores the
    event ID plus the sent flag. We cannot meaningfully migrate the old data, and it
    cannot be used going forward. This migration drops the content and allows it to
    be recycled by the new service version.

    This is obviously not reversible.
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        collection = self._db["notification_records"]

        # Drop the old notification records collection
        await collection.drop()
