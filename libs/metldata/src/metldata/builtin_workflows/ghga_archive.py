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

"""A GHGA Archive-specific workflow."""

from metldata.builtin_transformations.add_accessions import (
    ACCESSION_ADDITION_TRANSFORMATION,
)
from metldata.builtin_transformations.aggregate import AGGREGATE_TRANSFORMATION
from metldata.builtin_transformations.custom_embeddings import (
    CUSTOM_EMBEDDING_TRANSFORMATION,
)
from metldata.builtin_transformations.delete_slots import SLOT_DELETION_TRANSFORMATION
from metldata.builtin_transformations.infer_references import (
    REFERENCE_INFERENCE_TRANSFORMATION,
)
from metldata.builtin_transformations.merge_slots import SLOT_MERGING_TRANSFORMATION
from metldata.builtin_transformations.normalize_model import (
    NORMALIZATION_TRANSFORMATION,
)
from metldata.transform.base import WorkflowDefinition, WorkflowStep

GHGA_ARCHIVE_WORKFLOW = WorkflowDefinition(
    description=("A GHGA Archive-specific workflow"),
    steps={
        "normalize_model": WorkflowStep(
            description=("Transform the model to a canonical form."),
            transformation_definition=NORMALIZATION_TRANSFORMATION,
            input=None,
        ),
        "add_accessions": WorkflowStep(
            description="Add accessions that replace aliases as identifiers.",
            transformation_definition=ACCESSION_ADDITION_TRANSFORMATION,
            input="normalize_model",
        ),
        "embed_restricted": WorkflowStep(
            description=(
                "A step to generate a fully embedded metadata for data recipients that"
                + " have been granted controlled access to that dataset."
            ),
            transformation_definition=CUSTOM_EMBEDDING_TRANSFORMATION,
            input="add_accessions",
        ),
        "infer_multiway_references": WorkflowStep(
            description=(
                "Infer multi-way references. During submission, references between"
                + " two classes are only establish in a uni-lateral way from one of the"
                + " interlinked classes. Here references from both sides are"
                + " established. Moreover, shortcuts between entities that are"
                + " connected via a common reference are established."
            ),
            transformation_definition=REFERENCE_INFERENCE_TRANSFORMATION,
            input="add_accessions",
        ),
        "merge_dataset_file_lists": WorkflowStep(
            description=(
                "Generate a slot in that dataset that combines all files of different"
                + " type into a single list."
            ),
            transformation_definition=SLOT_MERGING_TRANSFORMATION,
            input="infer_multiway_references",
        ),
        "remove_restricted_metadata": WorkflowStep(
            description=(
                "Restricted metadata that shall not be publicly accessible is removed."
            ),
            transformation_definition=SLOT_DELETION_TRANSFORMATION,
            input="merge_dataset_file_lists",
        ),
        "aggregate_stats": WorkflowStep(
            description="Compute aggregate statistics.",
            transformation_definition=AGGREGATE_TRANSFORMATION,
            input="remove_restricted_metadata",
        ),
        "embed_public": WorkflowStep(
            description=(
                "A step to generate a fully embedded metadata resources for use in the"
                + " metadata catalog as the single dataset view."
            ),
            transformation_definition=CUSTOM_EMBEDDING_TRANSFORMATION,
            input="remove_restricted_metadata",
        ),
    },
    artifacts={
        "embedded_restricted": "embed_restricted",
        "resolved_restricted": "merge_dataset_file_lists",
        "resolved_public": "remove_restricted_metadata",
        "embedded_public": "embed_public",
        "stats_public": "aggregate_stats",
    },
)
