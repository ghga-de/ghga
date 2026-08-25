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
"""Returns a list of all the service directories."""

import os
from pathlib import Path

SERVICES_DIR = Path(__file__).parent.parent.parent.resolve() / "services"


def list_service_dirs() -> list[Path]:
    """Return a list of directories under the services folder."""
    return [
        folder
        for folder in (SERVICES_DIR / path for path in os.listdir(SERVICES_DIR))
        if folder.is_dir()
    ]


def validate_folder_name(folder_name: str) -> str:
    folder_names = [path.name for path in list_service_dirs()]
    folder_names.append("")

    if folder_name not in folder_names:
        print(
            f"Error: '{folder_name}' is not a valid folder. Choose from: {', '.join(folder_names)}"
        )
        exit(1)
    return folder_name
