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

"""This module contains functionalities for greeting persons."""

import random
from datetime import datetime

from ..models import Greeting, GreetingExpression

GREETINGS_EXPRESSIONS = [
    GreetingExpression(expression="Καλημέρα", language="Greek", isinformal=False),
    GreetingExpression(expression="Γεια σου", language="Greek", isinformal=True),
    GreetingExpression(expression="Γεια", language="Greek", isinformal=True),
    GreetingExpression(expression="Dobar dan", language="Croatian", isinformal=False),
    GreetingExpression(expression="Bok", language="Croatian", isinformal=True),
    GreetingExpression(expression="Zdravo", language="Croatian", isinformal=True),
    GreetingExpression(expression="Bonjour", language="French", isinformal=False),
    GreetingExpression(expression="Salut", language="French", isinformal=True),
    GreetingExpression(expression="Guten Tag", language="German", isinformal=False),
    GreetingExpression(expression="Moin moin", language="German", isinformal=True),
]


def generate_greeting(name: str, language: str, isinformal: bool):
    """Generate a greeting for a specific person."""

    # search for suitable expressions (might be multiple):
    expression_hits = [
        expr
        for expr in GREETINGS_EXPRESSIONS
        if expr.language == language and expr.isinformal == isinformal
    ]

    # throw error if no hits were found:
    if not expression_hits:
        raise ValueError(
            f'No greeting expressions found for language=="{language}" '
            'and isinformal="{isinformal}"'
        )

    # pick a random expression from the list of hits:
    expression = random.choice(expression_hits)  # nosec

    # assemble the greeting phrase:
    greeting_phrase = f"{expression.expression} {name}!"

    # return a Greeting object:
    return Greeting(
        message=greeting_phrase,
        created_at=datetime.now(),
        language=expression.language,
        isinformal=expression.isinformal,
    )
