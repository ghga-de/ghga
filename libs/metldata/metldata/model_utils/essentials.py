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

"""Basic constants and logic related to models."""

from __future__ import annotations

import dataclasses
import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator

import yaml
from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import SchemaDefinition

# The name of the root class of a model:
ROOT_CLASS = "Submission"


class MetadataModel(SchemaDefinition):
    """A dataclass for describing metadata models."""

    @classmethod
    def init_from_path(cls, model_path: Path) -> MetadataModel:
        """Initialize from a model file in yaml format."""

        with open(model_path, "r", encoding="utf-8") as file:
            model_json = yaml.safe_load(file)

        return cls(**model_json)

    @property
    def schema_view(self) -> ExportableSchemaView:
        """Get a schema view instance from the metadata model."""

        return ExportableSchemaView(self)

    def copy(self) -> MetadataModel:
        """Copy the model."""

        return deepcopy(self)

    def __eq__(self, other: object):
        """For comparisons."""

        if not isinstance(other, MetadataModel):
            return NotImplemented

        return self.as_dict() == other.as_dict()

    # pylint: disable=too-many-nested-blocks,too-many-branches
    def as_dict(self, essential: bool = True):  # noqa: C901
        """Get a dictionary representation of the model. If essential set to True, the
        dictionary will be cleaned of all fields that are not essential."""

        model_dict = dataclasses.asdict(self)

        if essential:
            if "classes" in model_dict:
                for class_ in model_dict["classes"].values():
                    if "from_schema" in class_:
                        del class_["from_schema"]
                    if "slot_usage" in class_:
                        for slot in class_["slot_usage"].values():
                            if "alias" in slot:
                                del slot["alias"]
                            if "from_schema" in slot:
                                del slot["from_schema"]
                            if "domain_of" in slot:
                                del slot["domain_of"]
            if "slots" in model_dict:
                for slot in model_dict["slots"].values():
                    if "from_schema" in slot:
                        del slot["from_schema"]
            if "enums" in model_dict:
                for enum in model_dict["enums"].values():
                    if "from_schema" in enum:
                        del enum["from_schema"]

        return model_dict

    def as_json(self) -> str:
        """Get a json representation of the model."""

        return json.dumps(self.as_dict(essential=True), indent=2)

    def as_yaml(self) -> str:
        """Get a yaml representation of the model."""

        return yaml.safe_dump(self.as_dict(essential=True))

    def write_yaml(self, path: Path) -> None:
        """Write the model to a yaml file."""

        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump(self.as_dict(essential=True), file)

    @contextmanager
    def temporary_yaml_path(self) -> Generator[Path, None, None]:
        """Returns a context manager that creates a temporary yaml file containing the
        model and returns its path on __enter__ and deletes it on __exit__.

        This is required because some tools in the linkml schema ecosystem only support
        working with paths to yaml file and not with in-memory representations.
        """

        with NamedTemporaryFile(mode="w", encoding="utf-8") as file:
            model_json = self.as_dict()
            yaml.safe_dump(model_json, file)
            file.flush()
            yield Path(file.name)

    def __hash__(self):
        """Return a hash of the model."""

        return hash(self.as_json())


class ExportableSchemaView(SchemaView):
    """Extend the SchemaView by adding a method for exporting a MetadataModel."""

    def export_model(self) -> MetadataModel:
        """Export a MetadataModel."""

        model_json = dataclasses.asdict(self.copy_schema())

        return MetadataModel(**model_json)
