# Copyright 2024 Kersten Henrik Breuer
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

"""A package to produce deeply (recursively) frozen Python data structures."""

from importlib.metadata import version

from ._internal._converters import STANDARD_CONVERTERS, Converter
from ._internal.freeze import ConverterNotFoundError, freeze
from ._internal.frozendict import FrozenDict

__all__ = [
    "ConverterNotFoundError",
    "freeze",
    "STANDARD_CONVERTERS",
    "Converter",
    "FrozenDict",
]

__version__ = version(__package__)
