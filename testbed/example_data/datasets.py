# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sample datasets for testing."""

from ghga_event_schemas.pydantic_ import (
    MetadataDatasetFile,
    MetadataDatasetOverview,
    MetadataDatasetStage,
)

DATASET_OVERVIEW_EVENT = MetadataDatasetOverview(
    accession="test-dataset-1",
    stage=MetadataDatasetStage.DOWNLOAD,
    title="Test Dataset 1",
    description="The first test dataset",
    files=[
        MetadataDatasetFile(
            accession="file-id-1",
            description="The first file",
            file_extension=".json",
        ),
        MetadataDatasetFile(
            accession="file-id-2",
            description="The second file",
            file_extension=".csv",
        ),
        MetadataDatasetFile(
            accession="file-id-3",
            description="The third file",
            file_extension=".bam",
        ),
    ],
)  # pyright: ignore
