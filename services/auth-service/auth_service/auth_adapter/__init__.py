# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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

"""Auth Adapter

The GHGA auth adapter is used by the API gateway via the ExtAuth protocol
to authenticate users on the edge and to convert the external access tokens
from the federated authentication service to internally access tokens.
"""

from auth_service import __version__

VERSION = __version__
TITLE = "Ext Auth Protocol"
DESCRIPTION = "Implementation of the Ext Auth protocol for the API gateway"
