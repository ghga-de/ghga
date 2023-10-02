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

"""A sub-package for translating server-side HTTP exceptions into client-side python
exceptions.
"""


# shortcuts:
from ghga_service_commons.httpyexpect.client.custom_types import Response  # noqa: F401
from ghga_service_commons.httpyexpect.client.mapping import (  # noqa: F401
    ExceptionMapping,
)
from ghga_service_commons.httpyexpect.client.translator import (  # noqa: F401
    ResponseTranslator,
)
