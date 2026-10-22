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

"""Pydantic types for the accessions of GHGA datasets and files."""

from typing import Annotated

from pydantic import StringConstraints

__all__ = [
    "BASE32_ALPHABET",
    "DATASET_PID_PREFIX",
    "RANDOM_BLOCK",
    "RANDOM_BLOCK_LENGTH",
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

RANDOM_BLOCK = rf"[{BASE32_ALPHABET}]{{{RANDOM_BLOCK_LENGTH}}}"
# the version V counts from 1, without leading zeros; [0-9] rather than \d, which
# Python widens to every Unicode digit while JSON Schema in openapi.yaml does not
STUDY_PID = rf"{STUDY_PID_PREFIX}\.[0-9]{{2}}\.{RANDOM_BLOCK}\.[1-9][0-9]*"

LEGACY_DATASET_ACCESSION = r"[A-Z]{1,6}[0-9]{3,18}"  # 'GHGAD12345…'
DATASET_PID = rf"{STUDY_PID}\.{DATASET_PID_PREFIX}\.{RANDOM_BLOCK}"

LEGACY_FILE_ACCESSION = r"GHGAF.+"  # 'GHGAF12345…'
# the alias part already expects aliases as metldata's `normalize_alias` (GSI-2697)
# writes them; update it whenever that rule changes
FILE_ACCESSION = rf"{STUDY_PID}\.[a-z0-9_-]+"  # '{study_pid}.{alias}'

DatasetAccession = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=rf"^(?:{LEGACY_DATASET_ACCESSION}|{DATASET_PID})$",
    ),
]

FileAccession = Annotated[
    str,
    StringConstraints(pattern=rf"^(?:{LEGACY_FILE_ACCESSION}|{FILE_ACCESSION})$"),
]
