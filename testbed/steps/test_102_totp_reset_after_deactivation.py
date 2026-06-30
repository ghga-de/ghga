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

"""Step definitions for TOTP reset after deactivation"""

import time

from .conftest import (
    JointFixture,
    given,
    parse,
    scenarios,
    when,
)

scenarios("../features/102_totp_reset_after_deactivation.feature")


@when(parse('"{full_name}" attempts TOTP verification with wrong codes'))
def deactivate_with_wrong_totp(full_name: str, fixtures: JointFixture):
    """Deactivate user with too many TOTP login attempts."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    sub = fixtures.auth.get_sub(full_name)
    totp_token = fixtures.state.get_state(f"totp-token-{sub}")
    assert totp_token, f"No TOTP token found for {full_name}"

    session_headers = fixtures.auth.headers(session)
    wrong_totp = fixtures.auth.generate_wrong_totp(totp_token)
    for i in range(fixtures.config.totp_max_failed_attempts + 1):
        if i == fixtures.config.totp_max_failed_attempts:
            # Pause for rate limits and processing before the final attempt
            time.sleep(1)
        response = fixtures.auth.verify_totp(wrong_totp, headers=session_headers)
        assert response.status_code == 401, response.text

    # Verify deactivation on the last response
    assert response.json().get("detail") == "Too many failed attempts", response.text
