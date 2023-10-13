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
"""This module provides the CachedMetadataModel class."""

from metldata.model_utils.anchors import AnchorPoint, get_anchors_points_by_target
from metldata.model_utils.essentials import MetadataModel


class CachedMetadataModel:
    """A model for a MetadataModel and pre-computed, non-dynamic associated
    anchor points by target and class names.
    """

    model: MetadataModel
    anchors_points_by_target: dict[str, AnchorPoint]
    all_class_names: list[str]

    def __init__(self, model: MetadataModel):
        self.model = model
        self.anchors_points_by_target = get_anchors_points_by_target(model=model)
        self.all_classes = list(model.schema_view.all_classes())
