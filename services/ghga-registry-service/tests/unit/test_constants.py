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

"""Guard against drift between field-name constants and the models they describe"""

from ghga_event_schemas.pydantic_ import ResearchDataUploadBox
from rs.constants import RDUB_OWNED_FIELDS, STAMP_FIELDS


def test_rdub_owned_fields_match_model():
    """RDUB_OWNED_FIELDS and STAMP_FIELDS are read via getattr() on a
    ResearchDataUploadBox instance in rdub_manager. If a field referenced there is
    renamed or removed on the model, that getattr() raises at runtime instead of at
    test time. Fail fast here instead.
    """
    model_fields = set(ResearchDataUploadBox.model_fields)
    assert RDUB_OWNED_FIELDS <= model_fields
    assert STAMP_FIELDS <= model_fields
