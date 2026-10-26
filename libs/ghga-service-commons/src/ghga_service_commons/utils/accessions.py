# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""The GHGA PID scheme: its constants, the patterns of study PIDs, dataset PIDs and
file accessions, and the Pydantic types for dataset and file accessions.
"""

from typing import Annotated

from pydantic import StringConstraints

__all__ = [
    "BASE32_ALPHABET",
    "DATASET_PID_PATTERN",
    "DATASET_PID_PREFIX",
    "FILE_ACCESSION_PATTERN",
    "RANDOM_BLOCK_LENGTH",
    "RANDOM_BLOCK_PATTERN",
    "STUDY_PID_PATTERN",
    "STUDY_PID_PREFIX",
    "DatasetAccession",
    "FileAccession",
]

# Not configurable: they build persistent identifiers, so changing one would break
# every PID already minted.
STUDY_PID_PREFIX = "GHGA"  # 'GHGA' in 'GHGA.YY.XXX.V'
DATASET_PID_PREFIX = "DS"  # 'DS' in '{study_pid}.DS.XXX'
RANDOM_BLOCK_LENGTH = 3  # 'XXX' in both; 32**3 = 32,768 study PIDs per year
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # RFC 4648, for 'XXX'

BASE32_PATTERN = r"[A-Z2-7]"  # BASE32_ALPHABET, spelled short for openapi.yaml
RANDOM_BLOCK_PATTERN = rf"{BASE32_PATTERN}{{{RANDOM_BLOCK_LENGTH}}}"
# the version V counts from 1, without leading zeros; [0-9] rather than \d, which
# Python widens to every Unicode digit while JSON Schema in openapi.yaml does not
STUDY_PID_PATTERN = (
    rf"{STUDY_PID_PREFIX}\.[0-9]{{2}}\.{RANDOM_BLOCK_PATTERN}\.[1-9][0-9]*"
)

LEGACY_DATASET_ACCESSION_PATTERN = r"[A-Z]{1,6}[0-9]{3,18}"  # 'GHGAD12345…'
DATASET_PID_PATTERN = (
    rf"{STUDY_PID_PATTERN}\.{DATASET_PID_PREFIX}\.{RANDOM_BLOCK_PATTERN}"
)

LEGACY_FILE_ACCESSION_PATTERN = r"GHGAF.+"  # 'GHGAF12345…'
# '{study_pid}.{alias}'; the alias part already expects aliases as metldata's
# `normalize_alias` (GSI-2697) writes them; update it whenever that rule changes
FILE_ACCESSION_PATTERN = rf"{STUDY_PID_PATTERN}\.[a-z0-9_-]+"

DatasetAccession = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=rf"^(?:{LEGACY_DATASET_ACCESSION_PATTERN}|{DATASET_PID_PATTERN})$",
    ),
]

FileAccession = Annotated[
    str,
    StringConstraints(
        pattern=rf"^(?:{LEGACY_FILE_ACCESSION_PATTERN}|{FILE_ACCESSION_PATTERN})$"
    ),
]
