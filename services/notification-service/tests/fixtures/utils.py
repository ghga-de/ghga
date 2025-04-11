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

"""Utils for Fixture handling"""

import socket
from pathlib import Path

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import JsonObject

BASE_DIR = Path(__file__).parent.resolve()


def make_notification(payload: JsonObject):
    """Convenience method to produce a validated notification object"""
    return get_validated_payload(payload=payload, schema=event_schemas.Notification)


def get_free_port() -> int:
    """Finds and returns a free port on localhost."""
    sock = socket.socket()
    sock.bind(("", 0))
    return int(sock.getsockname()[1])
