# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

"""Greeting fixtures"""

import os
from copy import deepcopy
from typing import List

from my_microservice.core.greeting import GREETINGS_EXPRESSIONS
from my_microservice.models import GreetingExpression

from ...fixtures.utils import read_yaml
from . import BASE_DIR

GREETING_EXPRESSIONS_YAML = os.path.join(BASE_DIR, "greeting_expressions.yaml")
GREETINGS_EXPRESSIONS_BACKUP = deepcopy(GREETINGS_EXPRESSIONS)


class GreetingExpressionsFixture:
    """Handler for greeting expression fixtures with a
    context manager for overwriting (patch) the default
    GREETINGS_EXPRESSIONS list."""

    expressions: List[GreetingExpression]

    def __init__(self):
        expression_dicts = read_yaml(GREETING_EXPRESSIONS_YAML)
        self.expressions = [GreetingExpression(**expr) for expr in expression_dicts]

    def __enter__(self):
        """overwrite GREETING_EXPRESSIONS"""
        GREETINGS_EXPRESSIONS.clear()
        GREETINGS_EXPRESSIONS.extend(self.expressions)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore default GREETINGS_EXPRESSIONS"""
        GREETINGS_EXPRESSIONS.clear()
        GREETINGS_EXPRESSIONS.extend(GREETINGS_EXPRESSIONS_BACKUP)


greeting_expression_fixture = GreetingExpressionsFixture()
