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

"""A subpackage containing the framework for defining converters (for converting
individual potentially mutable types into immutable types) and the standard converters
that come with this library."""

from .base import (
    STANDARD_MUTABLE_PRIORITY,
    STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY,
    STANDARD_PRIMITIVE_PRIORITY,
    Converter,
)
from .standard import STANDARD_CONVERTERS

__all__ = [
    "STANDARD_CONVERTERS",
    "STANDARD_MUTABLE_PRIORITY",
    "STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY",
    "STANDARD_PRIMITIVE_PRIORITY",
    "Converter",
]
