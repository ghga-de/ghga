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

"""A testcontainer for running the mock app in the background."""

from pathlib import Path

import requests
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_container_is_ready

APP_MODULE_PATH = Path(__file__).parent.resolve() / "app.py"


class MockAPIContainer(DockerContainer):
    """
    Test container for FastAPI.

    """

    def __init__(
        self,
        s3_download_url: str = "test://download.url",
        s3_upload_url_1: str = "test://upload.url",
        s3_upload_url_2: str = "test://upload.url",
        s3_download_file_size: int = 146,
        fake_envelope: str = "Fake_envelope",
        image: str = "ghga/fastapi_essentials:0.94.1",
        port: int = 8000,
    ) -> None:
        """Initialize the Fastapi test container.

        Args:
            image (str, optional):
                The docker image from docker hub. Defaults to "ghga/fastapi_essentials:0.94.1".
            port (int, optional):
                The port to reach the FastAPI. Defaults to 8000.
        """
        super().__init__(image=image)

        self._port = port

        self.with_exposed_ports(self._port)
        self.with_env("S3_DOWNLOAD_URL", s3_download_url)
        self.with_env("S3_UPLOAD_URL_1", s3_upload_url_1)
        self.with_env("S3_UPLOAD_URL_2", s3_upload_url_2)
        self.with_env("S3_DOWNLOAD_FIELD_SIZE", s3_download_file_size)
        self.with_env("FAKE_HEADER_ENVELOPE", fake_envelope)
        self.with_volume_mapping(host=str(APP_MODULE_PATH), container="/app.py")
        self.with_command(
            f"python3 -m uvicorn --host 0.0.0.0 --port {self._port} --app-dir / app:app"
        )

    def get_connection_url(self) -> str:
        """Returns an HTTP connection URL to the API root."""
        ip = self.get_container_host_ip()
        port = self.get_exposed_port(self._port)
        return f"http://{ip}:{port}"

    @wait_container_is_ready()
    def readiness_probe(self):
        """Test if the RabbitMQ broker is ready."""
        connection_url = self.get_connection_url()
        request = requests.get(f"{connection_url}/ready", timeout=0.5)

        if request.status_code != 204:
            raise RuntimeError("Mock API server not ready.")

    def start(self):
        """Start the test container."""
        super().start()
        self.readiness_probe()
        return self
