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

"""Contains abstract message display base class"""

import enum
from abc import ABC, abstractmethod


class AbstractMessageDisplay(ABC):
    """Simple message display base class"""

    @abstractmethod
    def display(self, message: str):
        """Display a message with standard formatting"""

    @abstractmethod
    def success(self, message: str):
        """Display a message representing information about a successful operation"""

    @abstractmethod
    def failure(self, message: str):
        """Display a message representing information about a failed operation"""


class MessageColors(str, enum.Enum):
    """
    Define commonly used colors for logging
    For a selection of valid colors see click.termui._ansi_colors:
    https://github.com/pallets/click/blob/c96545f6f4ba0eab99de6ec8b4ceb77c9bdb2528/src/click/termui.py#L30
    """

    DEFAULT = "white"
    SUCCESS = "green"
    FAILURE = "red"
