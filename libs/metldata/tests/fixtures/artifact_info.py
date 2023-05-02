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

"""Example of ArtifactInfo objects."""

from metldata.artifacts_rest.artifact_info import load_artifact_info
from tests.fixtures.metadata_models import VALID_MINIMAL_METADATA_MODEL
from tests.fixtures.workflows import EXAMPLE_ARTIFACT_MODELS

# artifact info for the minimal valid metadata model:
MINIMAL_ARTIFACT_INFO = load_artifact_info(
    name="valid_minimal_metadata_model",
    description="This is a minimal valid metadata model.",
    model=VALID_MINIMAL_METADATA_MODEL,
)

# artifact infos for the example workflow:
EXAMPLE_ARTIFACT_INFOS = [
    load_artifact_info(
        name=artifact_name, description=artifact_name, model=artifact_model
    )
    for artifact_name, artifact_model in EXAMPLE_ARTIFACT_MODELS.items()
]
