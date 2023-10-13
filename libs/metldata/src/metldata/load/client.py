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
#

"""Client functionality to drop artifacts onto the endpoint for uploading them."""

import httpx

from metldata.event_handling.event_handling import FileSystemEventCollector
from metldata.load.collect import collect_artifacts
from metldata.load.config import ArtifactLoaderClientConfig


class ArtifactUploadException(Exception):
    """Exception raised when uploading artifacts fails."""


def upload_artifacts_via_http_api(
    *, token: str, config: ArtifactLoaderClientConfig
) -> None:
    """Upload artifacts via the HTTP API specified in the config using the provided
    token for authorization.

    Raises:
        ArtifactUploadException: If uploading artifacts fails.
    """
    event_collector = FileSystemEventCollector(config=config)
    artifacts = collect_artifacts(config=config, event_collector=event_collector)

    with httpx.Client() as client:
        response = client.post(
            f"{config.loader_api_root}/rpc/load-artifacts",
            json=artifacts,
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=60,
        )

    if response.status_code != 204:
        raise ArtifactUploadException(
            f"Uploading artifacts failed with status code {response.status_code}."
        )
