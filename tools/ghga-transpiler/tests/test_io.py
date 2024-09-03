# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

"""IO functionality tests"""

import json
from pathlib import Path

import pytest
import yaml

from ghga_transpiler import transpiler_io

from .fixtures.test_data_objects.conversion_data import (
    EXPECTED_CONVERSION_DATAPACK,
    EXPECTED_CONVERSION_JSON,
)


def test_write_datapack_json(tmp_path: Path):
    """Test write_datapack in JSON format"""
    out_path = tmp_path.joinpath("out.json")
    transpiler_io.write_datapack(
        data=EXPECTED_CONVERSION_DATAPACK, path=out_path, yaml_format=False, force=False
    )

    with open(file=out_path, encoding="utf8") as in_file:
        data = json.load(fp=in_file)
    assert data == EXPECTED_CONVERSION_JSON


def test_write_datapack_yaml(tmp_path: Path):
    """Test write_datapack in YAML format"""
    out_path = tmp_path.joinpath("out.yaml")
    transpiler_io.write_datapack(
        data=EXPECTED_CONVERSION_DATAPACK, path=out_path, yaml_format=True, force=False
    )

    with open(file=out_path, encoding="utf8") as in_file:
        data = yaml.safe_load(in_file)
    assert data == EXPECTED_CONVERSION_JSON


def test_write_datapack_json_force(tmp_path: Path):
    """Test write_json overwrite of output"""
    out_path = tmp_path.joinpath("out.json")
    out_path.touch()
    transpiler_io.write_datapack(
        data=EXPECTED_CONVERSION_DATAPACK, path=out_path, yaml_format=False, force=True
    )


def test_write_datapack_yaml_force(tmp_path):
    """Test write_yaml overwrite of output"""
    out_path = tmp_path.joinpath("out.yaml")
    out_path.touch()
    transpiler_io.write_datapack(
        data=EXPECTED_CONVERSION_DATAPACK, path=out_path, yaml_format=True, force=True
    )


@pytest.mark.parametrize(
    "yaml_format", [True, False], ids=["yaml_format", "json_format"]
)
def test_write_datapack_no_force(tmp_path: Path, yaml_format: bool):
    """Test write_datapack abort if output exists"""
    ext = "yaml" if yaml_format else "json"
    out_path = tmp_path.joinpath(f"out.{ext}")
    out_path.touch()
    with pytest.raises(FileExistsError):
        transpiler_io.write_datapack(
            data=EXPECTED_CONVERSION_DATAPACK,
            path=out_path,
            yaml_format=yaml_format,
            force=False,
        )


@pytest.mark.parametrize(
    "yaml_format", [True, False], ids=["yaml_format", "json_format"]
)
def test_write_datapack_stdout(capfd: pytest.CaptureFixture[str], yaml_format: bool):
    """Test write_datapack overwrite of output"""
    transpiler_io.write_datapack(
        data=EXPECTED_CONVERSION_DATAPACK,
        path=None,
        yaml_format=yaml_format,
        force=True,
    )
    captured = capfd.readouterr()
    data = yaml.safe_load(captured.out) if yaml_format else json.loads(captured.out)
    assert data == EXPECTED_CONVERSION_JSON
