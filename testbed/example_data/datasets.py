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

# We simulate the emission of the dataset overview event
# since it is currently not yet implemented.
# After this has been implemented, this file should be removed.

DATASET_OVERVIEW_EVENT = MetadataDatasetOverview(
    accession="DS_1",
    stage=MetadataDatasetStage.DOWNLOAD,
    title="The A dataset",
    description="An interesting dataset A",
    files=[
        MetadataDatasetFile(
            accession="STUDY_FILE_1",
            description="The first study file",
            file_extension=".fastq.gz",
        )
    ],
)  # pyright: ignore
