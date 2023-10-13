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

"""A self expanding defaultdict which allows to address arbitrary data paths."""

from collections import defaultdict
from typing import Any


class ExpandingDict(defaultdict):
    """Rudimentary implementation of a self expanding default dict with no error
    checking
    """

    def __init__(self):
        """Create a new ExpandingDict"""
        defaultdict.__init__(self, self.__class__)

    def __resolve_path(self, path: str) -> tuple:
        """Resolves the given string representation of a path by dot-splitting
        the path. Returns the terminal key and the pre-terminal dictionary.

        Args:
            path (str): A string representation of path. Example: foo.bar.baz

        Returns:
            tuple: (dict, key) the pre-terminal dictionary and the terminal key
        """
        cur = self
        nodes = path.split(".")
        for node in nodes[:-1]:
            cur = cur[node]
        return cur, nodes[-1]

    def set_path_value(self, path: str, value: Any) -> None:
        """Set a value in the expanding dict based on a string representation of
        the key path.

        Warning: Does not perform type checking of intermediate data structures.

        Args:
            path (str): A key path. Example: foo.bar.baz
            value (Any): A value to set
        """
        holder, key = self.__resolve_path(path)
        holder[key] = value

    def get_path_value(self, path: str) -> Any:
        """Get a value in the expanding dict based on a string representation of
        the key path.

        Warning: Does not perform type checking of intermediate data structures.

        Args:
            path (str): A key path. Example: foo.bar.baz

        Returns:
            Any: The value.
        """
        holder, key = self.__resolve_path(path)
        return holder[key]

    def to_dict(self) -> dict:
        """Recursively convert the expanding dict to a regular dictionary"""
        return {
            key: value.to_dict() if isinstance(value, ExpandingDict) else value
            for key, value in self.items()
        }
