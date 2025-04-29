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
#

"""Sample datasets for testing."""

from ghga_event_schemas.pydantic_ import (
    MetadataDatasetID,
    MetadataDatasetOverview,
    MetadataDatasetStage,
)

from ars.core.models import Dataset

__all__ = ["DATASET", "DATASET_DELETION_EVENT", "DATASET_UPSERTION_EVENT"]


DATASET = Dataset(
    id="some-dataset-id",
    title="Some dataset",
    description="This dataset is used for testing",
    dac_alias="Some DAC",
)


DATASET_UPSERTION_EVENT = MetadataDatasetOverview(
    accession="some-dataset-id",
    stage=MetadataDatasetStage.DOWNLOAD,
    title="Some dataset",
    description="This dataset is used for testing",
    dac_alias="Some DAC",
    files=[],
)


DATASET_DELETION_EVENT = MetadataDatasetID(
    accession="some-dataset-id",
)
