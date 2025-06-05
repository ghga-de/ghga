# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""A specification (plus tooling) for describing linked data models based on JSON
schema.
"""

from importlib.metadata import version

from ._internals.dump import dump_schemapack, dumps_datapack, dumps_schemapack
from ._internals.erd import export_mermaid
from ._internals.isolate import isolate, isolate_class, isolate_resource
from ._internals.load import load_datapack, load_schemapack
from ._internals.main import load_and_validate
from ._internals.normalize import denormalize
from ._internals.validation import SchemaPackValidator

__all__ = [
    "SchemaPackValidator",
    "denormalize",
    "dump_schemapack",
    "dumps_datapack",
    "dumps_schemapack",
    "export_mermaid",
    "isolate",
    "isolate_class",
    "isolate_resource",
    "load_and_validate",
    "load_datapack",
    "load_schemapack",
]

__version__ = version(__package__)
