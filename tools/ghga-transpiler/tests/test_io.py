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

import pytest

from ghga_transpiler import io

from .fixtures.test_data_objects.conversion_data import EXPECTED_CONVERSION


def test_write_json_file(tmp_path):
    """Test write_json"""
    out_path = tmp_path.joinpath("out.json")
    io.write_json(data=EXPECTED_CONVERSION, path=out_path, force=False)

    with open(file=out_path, encoding="utf8") as in_file:
        data = json.load(fp=in_file)
    assert data == EXPECTED_CONVERSION


def test_write_json_file_force(tmp_path):
    """Test write_json overwrite of output"""
    out_path = tmp_path.joinpath("out.json")
    out_path.touch()
    io.write_json(data=EXPECTED_CONVERSION, path=out_path, force=True)


def test_write_json_file_no_force(tmp_path):
    """Test write_json abort if output exists"""
    out_path = tmp_path.joinpath("out.json")
    out_path.touch()
    with pytest.raises(FileExistsError):
        io.write_json(data=EXPECTED_CONVERSION, path=out_path, force=False)


def test_write_json_file_stdout(capfd):
    """Test write_json overwrite of output"""
    io.write_json(data=EXPECTED_CONVERSION, path=None, force=True)
    captured = capfd.readouterr()
    data = json.loads(captured.out)
    assert data == EXPECTED_CONVERSION
