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

"""Service-wide constants"""

from opentelemetry import trace

SERVICE_NAME = "uos"
TRACER = trace.get_tracer_provider().get_tracer(SERVICE_NAME)
BOX_COLLECTION = "boxes"
AUDIT_COLLECTION = "auditLogs"
WORK_ORDER_TOKEN_VALID_SECONDS = 30
ACCESSION_MAPS_COLLECTION = "accessionMaps"
HTTPX_TIMEOUT = 60
VALID_STATE_TRANSITIONS = [
    ("open", "locked"),
    ("locked", "open"),
    ("locked", "archived"),
]
