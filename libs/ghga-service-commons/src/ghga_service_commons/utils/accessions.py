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

__all__ = ["DatasetAccession", "FileAccession"]

# the study PID and dataset prefixes are not spelled out, as metldata makes them
# configurable
BASE32 = r"[A-Z2-7]"  # RFC 4648 alphabet of the random blocks
STUDY_PID = rf"[^.\s]+\.\d{{2}}\.{BASE32}+\.\d+"  # 'PREFIX.YY.XXX.V'

LEGACY_DATASET_ACCESSION = r"[A-Z]{1,6}[0-9]{3,18}"  # 'GHGAD12345…'
DATASET_PID = rf"{STUDY_PID}\.[^.\s]+\.{BASE32}+"  # '{study_pid}.DS.XXX'

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
