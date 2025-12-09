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
"""Some constants for testing, mostly IDs"""

from uuid import UUID, uuid4

SOME_USER_ID = UUID("849dab6f-0ee3-43c9-9060-68c6fc899082")

ID_OF_JOHN_DOE = UUID("f031970d-69c1-4552-842f-84e45e544a49")
ID_OF_ROD_STEWARD = UUID("25bae981-2c67-43ce-983b-2621487d5ad3")
ID_OF_JOHN = UUID("c2905127-5e57-4e46-b24b-9687891e921f")
EXT_ID_OF_JOHN = "john@aai.org"
ID_OF_JAMES = UUID("198a85e5-6327-4eef-b184-e683742abfac")
EXT_ID_OF_JAMES = "james@aai.org"
ID_OF_JANE = UUID("bc29cf37-07ff-4d2a-8778-597d1da8d169")
EXT_ID_OF_JANE = "jane@aai.org"
ID_OF_MAX = UUID("09fa2bb1-ffa5-44fa-8117-887acf518c63")
ID_OF_STEVE = UUID("8969a086-9b1c-42bc-99da-efe0b8dc0c74")

# A mapping that approximates the old test behavior of replacing the string's email domain
EXT_TO_INT_ID = {
    EXT_ID_OF_JAMES: ID_OF_JAMES,
    EXT_ID_OF_JANE: ID_OF_JANE,
    EXT_ID_OF_JOHN: ID_OF_JOHN,
}

SOME_IVA_ID = UUID("2c760cfd-a4f0-4e0a-8f6d-5a4869ed8443")

DATA_STEWARD_IVA_ID = UUID("557f7967-aa92-442c-a2b3-24e441d2b3fc")
DATA_STEWARD_CLAIM_ID = UUID("d06b1e82-45f3-4de1-be38-5bdb785e49da")
DATA_ACCESS_IVA_ID = UUID("e5b5a299-4440-443c-ad53-8dadfcd8fc3a")
DATA_ACCESS_CLAIM_ID = UUID("7ca22877-ba98-445e-8c3a-6598d36be4d7")

IVA_IDS = [uuid4() for _ in range(20)]

SOME_CLAIM_ID = UUID("9f43747d-9f84-43a3-bc8e-36cfb04d0cb6")

PHONE_OF_JOHN = "+491710000001"
PHONE_OF_JAMES = "+491720000002"
PHONE_OF_JANE = "+491730000003"
