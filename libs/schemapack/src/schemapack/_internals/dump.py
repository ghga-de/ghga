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

"""Logic for dumping schemapacks."""

import json
from pathlib import Path
from typing import Any

import ruamel.yaml

from schemapack._internals.spec.schemapack import SchemaPack

yaml = ruamel.yaml.YAML(typ="safe")
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False


def get_content_schema_path(*, class_name: str, content_schema_dir: Path) -> Path:
    """Get the path to a content schema file in the provided directory for a class with
    the provided name.
    """
    return content_schema_dir / f"{class_name}.schema.json"


def set_content_schema_paths(
    *, schemapack_dict: dict[str, Any], content_schema_dir: Path
) -> dict[str, Any]:
    """Sets the content schema paths in the provided schemapack dictionary.

    Returns:
        A copy of the provided schemapack dictionary with the content schema paths set.
    """
    modified_classes = {
        class_name: {
            **class_,
            "content": str(
                get_content_schema_path(
                    class_name=class_name, content_schema_dir=content_schema_dir
                )
            ),
        }
        for class_name, class_ in schemapack_dict["classes"].items()
    }

    return {**schemapack_dict, "classes": modified_classes}


def write_schemapack_dict(
    schemapack_dict: dict, *, path: Path, yaml_format: bool
) -> None:
    """Writes the provided schemapack dictionary to a file at the provided path."""
    if yaml_format:
        with open(path, "w", encoding="utf-8") as file:
            yaml.dump(schemapack_dict, file)
    else:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(schemapack_dict, file, indent=2)


def write_content_schemas(
    *, schemapack: SchemaPack, content_schema_dir: Path, relative_to: Path
) -> None:
    """Writes the content schemas of individual classes defined in the provided
    schemapack as separate files to the provided directory `content_schema_dir`
    which is relative to `relative_to`.
    """
    abs_content_schema_dir = relative_to / content_schema_dir
    abs_content_schema_dir.mkdir(parents=True, exist_ok=True)

    for class_name, class_ in schemapack.classes.items():
        content_schema_path = get_content_schema_path(
            class_name=class_name, content_schema_dir=abs_content_schema_dir
        )
        with open(content_schema_path, "w", encoding="utf-8") as file:
            file.write(class_.content.json_schema)


def dump_schemapack(
    schemapack: SchemaPack,
    *,
    path: Path,
    condensed: bool = True,
    content_schema_dir: Path = Path("content_schemas"),
    yaml_format: bool = True,
) -> None:
    """Dumps the provided schemapack as a JSON or YAML file to the provided path.

    Args:
        schemapack:
            The schemapack to dump.
        path:
            The file path to write the schemapack to. The parent directory has to exist.
            If the file already exists, it will be overwritten.
        condensed:
            Whether to dump a condensed version (i.e. with content schemas embedded) of
            the provided schemapack.
        content_schema_dir:
            The path to the directory used to output the content schemas of individual
            classes defined in the provided schemapack as separate files. The path is
            relative to the `path` of the schemapack. If it does not exist, it will be
            created. The content schema files are always in JSON format and named
            according to the class name '{class_name}.schema.json'.
            Please note, this is only relevant if `condensed` is set to `False`.
        yaml_format:
            Whether to dump as YAML (`True`) or JSON (`False`).

    Raises:
        FileNotFoundError:
            If the parent directory of the provided `path` does not exist.
    """
    parent_dir = path.parent
    if not parent_dir.exists():
        raise FileNotFoundError(f"The parent directory of '{path}' does not exist.")

    schemapack_dict = json.loads(schemapack.model_dump_json(exclude_defaults=True))

    if not condensed:
        schemapack_dict = set_content_schema_paths(
            schemapack_dict=schemapack_dict, content_schema_dir=content_schema_dir
        )
        write_content_schemas(
            schemapack=schemapack,
            content_schema_dir=content_schema_dir,
            relative_to=parent_dir,
        )

    write_schemapack_dict(schemapack_dict, path=path, yaml_format=yaml_format)
