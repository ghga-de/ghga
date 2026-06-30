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
#

"""Sample datasets for testing."""

from uuid import UUID

from ghga_event_schemas.pydantic_ import (
    FileAccessionMapping,
    MetadataDatasetFile,
    MetadataDatasetID,
    MetadataDatasetOverview,
    MetadataDatasetStage,
)

from wps.core.models import (
    Dataset,
    DatasetFile,
    WorkPackageType,
)

__all__ = [
    "DATASET",
    "DATASET_DELETION_EVENT",
    "DATASET_UPSERTION_EVENT",
    "FILE_ACCESSION_MAPS",
    "FILE_ACCESSION_MAP_DOCS",
]


DATASET = Dataset(
    id="some-dataset-id",
    title="Test dataset 1",
    stage=WorkPackageType.DOWNLOAD,
    description="The first test dataset",
    files=[
        DatasetFile(accession="GHGAF01", extension=".json"),
        DatasetFile(accession="GHGAF02", extension=".csv"),
        DatasetFile(accession="GHGAF03", extension=".bam"),
    ],
)


DATASET_UPSERTION_EVENT = MetadataDatasetOverview(
    accession="some-dataset-id",
    stage=MetadataDatasetStage.DOWNLOAD,
    title="Test dataset 1",
    description="The first test dataset",
    dac_alias="Some DAC",
    dac_email="dac@some.org",
    files=[
        MetadataDatasetFile(
            accession="GHGAF01",
            description="The first file",
            file_extension=".json",
        ),
        MetadataDatasetFile(
            accession="GHGAF02",
            description="The second file",
            file_extension=".csv",
        ),
        MetadataDatasetFile(
            accession="GHGAF03",
            description="The third file",
            file_extension=".bam",
        ),
    ],
)

FILE_ACCESSION_MAP_DOCS: list[dict] = [
    {"_id": "GHGAF01", "file_id": UUID("ed42650f-a683-4300-ad41-6d13e33b45eb")},
    {"_id": "GHGAF02", "file_id": UUID("abeffa71-37d0-4a4b-8b6d-c66e8a15af41")},
    {"_id": "GHGAF03", "file_id": UUID("d1038bd8-7a04-40ba-8a3d-9eb4146b02e9")},
]

FILE_ACCESSION_MAPS = [
    FileAccessionMapping(accession=doc["_id"], file_id=doc["file_id"])
    for doc in FILE_ACCESSION_MAP_DOCS
]


DATASET_DELETION_EVENT = MetadataDatasetID(
    accession="some-dataset-id",
)
