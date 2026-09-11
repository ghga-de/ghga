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

SERVICE_NAME: str = "rs"
TRACER = trace.get_tracer_provider().get_tracer(SERVICE_NAME)
RESEARCH_DATA_UPLOAD_BOX_COLLECTION = "researchDataUploadBoxes"
AUDIT_COLLECTION = "auditLogs"
WORK_ORDER_TOKEN_VALID_SECONDS = 30
FILE_ACCESSION_COLLECTION = "fileAccessions"
STUDY_COLLECTION = "studies"
HTTPX_TIMEOUT = 60
UCS_UPLOADS_PAGE_SIZE = 100
VALID_STATE_TRANSITIONS = [
    ("open", "locked"),
    ("locked", "open"),
    ("locked", "archived"),
]

# HTTP exception IDs, returned by RS and/or expected from UCS responses
EXC_ID_ACCESSION_MAP_ERROR = "accessionMapError"
EXC_ID_ARCHIVAL_PREREQS_NOT_MET = "archivalPrereqsNotMet"
EXC_ID_BOX_MAX_SIZE_TOO_LOW = "boxMaxSizeTooLow"
EXC_ID_BOX_NOT_FOUND = "boxNotFound"
EXC_ID_BOX_STATE_ERROR = "boxStateError"
EXC_ID_BOX_TITLE_EXISTS = "boxTitleExists"
EXC_ID_BOX_VERSION_OUTDATED = "boxVersionOutdated"
EXC_ID_GRANT_NOT_FOUND = "grantNotFound"
EXC_ID_INCOMPLETE_OR_FAILED = "incompleteOrFailed"
EXC_ID_INTERNAL_ERROR = "internalError"
EXC_ID_INVALID_STATE_CHANGE = "invalidStateChange"
EXC_ID_NOT_AUTHORIZED = "notAuthorized"
EXC_ID_STUDY_NOT_FOUND = "studyNotFound"
