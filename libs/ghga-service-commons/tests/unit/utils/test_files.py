# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the utilities for working with files."""

import pytest

from ghga_service_commons.utils.files import get_file_extension

FILENAMES_AND_EXTENSIONS = {
    "foo": "",
    "foo.bar": ".bar",
    "foo.csv": ".csv",
    "foo.csv.gz": ".csv.gz",
    "foo.csv.gz.bz2": ".csv.gz.bz2",
    "gz.bz2": ".bz2",
    "bz2.gz": ".gz",
    "foo.zip": ".zip",
    "foo.bar.zip": ".zip",
    "foo.7z": ".7z",
    "foo.bar.7z": ".7z",
    "foo.csv.bz2": ".csv.bz2",
    "foo.csv.tar.gz": ".tar.gz",
    "foo.csv.tgz": ".tgz",
    "foo.fastq": ".fastq",
    "foo.cram.gz": ".cram.gz",
    "foo.fasta.genozip": ".fasta.genozip",
    "metadata.json": ".json",
    "metadata.json.bz2": ".json.bz2",
    "SEQ_FILE_A_R1.fastq.gz": ".fastq.gz",
    "SAMPLE_1_SPECIMEN_1_FILE_1.vcf.gz": ".vcf.gz",
    "some.data.log.xz": ".log.xz",
    "sample v0.1.0.gz": ".gz",
    "sample v0.1.0.fasta.gz": ".fasta.gz",
    "sample_2023.08.01.bz2": ".bz2",
    "sample_2023.08.01.bam.bz2": ".bam.bz2",
}


@pytest.mark.parametrize("filename,expected", FILENAMES_AND_EXTENSIONS.items())
def test_get_extension(filename: str, expected: str):
    """Test that the extension is extracted properly from the example filenames."""
    assert get_file_extension(filename) == expected
