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

"""Test reference utils."""

from metldata.builtin_transformations.infer_references.config import (
    ReferenceInferenceConfig,
)
from metldata.builtin_transformations.infer_references.path.path import ReferencePath
from metldata.builtin_transformations.infer_references.reference import (
    InferredReference,
)


def test_config():
    """Test the ReferenceInferenceConfig class."""

    inferred_ref_map = {
        "class_a": {
            "class_d": {
                "path": "class_a(class_b)>class_b(class_d)>class_d",
                "multivalued": False,
            },
            "class_c": {
                "path": "class_a(class_b)>class_b<(class_c)class_c",
                "multivalued": True,
            },
        },
        "class_b": {
            "class_c": {
                "path": "class_b<(class_c)class_c",
                "multivalued": True,
            }
        },
    }
    expected_refs = [
        InferredReference(
            source="class_a",
            target="class_d",
            path=ReferencePath(path_str="class_a(class_b)>class_b(class_d)>class_d"),
            new_slot="class_d",
            multivalued=False,
        ),
        InferredReference(
            source="class_a",
            target="class_c",
            path=ReferencePath(path_str="class_a(class_b)>class_b<(class_c)class_c"),
            new_slot="class_c",
            multivalued=True,
        ),
        InferredReference(
            source="class_b",
            target="class_c",
            path=ReferencePath(path_str="class_b<(class_c)class_c"),
            new_slot="class_c",
            multivalued=True,
        ),
    ]

    config = ReferenceInferenceConfig(inferred_ref_map=inferred_ref_map)
    observed_refs = config.inferred_references
    assert expected_refs == observed_refs
