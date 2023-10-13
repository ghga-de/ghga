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

"""Config Parameter Modeling and Parsing"""

from hexkit.config import config_from_yaml

# pylint: disable=unused-import
from metldata.accession_registry.config import Config as AccessionRegistryConfig
from metldata.artifacts_rest.config import ArtifactsRestConfig

# pylint: disable=unused-import
from metldata.load.config import ArtifactLoaderAPIConfig
from metldata.submission_registry.config import Config as SubmissionRegistryConfig


# pylint: disable=too-many-ancestors
@config_from_yaml(prefix="metl_sub")
class SubmissionConfig(AccessionRegistryConfig, SubmissionRegistryConfig):
    """Config parameters and their defaults."""


@config_from_yaml(prefix="metldata")
class Config(ArtifactLoaderAPIConfig, ArtifactsRestConfig):
    """Config parameters and their defaults."""

    service_name: str = "metldata"
