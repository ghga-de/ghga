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

"""Step definition for user session after account inactivation"""

import pytest
from pytest_bdd import (  # noqa: RUF100
    given,
    scenarios,
    then,
    when,
)

from .conftest import JointFixture, Response, parse

scenarios("../features/301_user_session_after_inactivation.feature")


@given(parse('the status of "{full_name}" is "{status}"'))
def user_status(full_name: str, status: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(full_name)
    saved_status = fixtures.state.get_state(f"status-{sub}")
    assert saved_status, (
        f'Saved status "{saved_status}" does not match with the expected'
    )
