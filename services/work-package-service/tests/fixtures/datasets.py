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

from ghga_event_schemas.pydantic_ import MetadataDatasetFile, MetadataDatasetOverview

from wps.core.models import Dataset, DatasetFile

__all__ = ["DATASET", "DATASET_OVERVIEW_EVENT"]


DATASET = Dataset(
    id="some-dataset-id",
    title="Test dataset 1",
    description="The first test dataset",
    files=[
        DatasetFile(id="file-id-1", description="The first file", extension=".json"),
        DatasetFile(id="file-id-2", description="The second file", extension=".csv"),
        DatasetFile(id="file-id-3", description="The third file", extension=".bam"),
    ],
)


DATASET_OVERVIEW_EVENT = MetadataDatasetOverview(
    accession="some-dataset-id",
    title="Test dataset 1",
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
)
