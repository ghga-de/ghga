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

"""Tests for the content of the notifications."""

from nos.core.notifications import (
    DIFFERENT_EMAILS_NOTE,
    SAME_EMAILS_NOTE,
    requester_emails,
)

LS_LOGIN_LINE = "LS Login email (preferred address in LS Login): doe@home.org"


def test_requester_emails_different():
    """Test that differing emails are both shown with an explanation."""
    text = requester_emails(
        contact_email="doe@institute.org", ls_login_email="doe@home.org"
    )
    assert text == (
        "Contact email for this request: doe@institute.org\n"
        f"{LS_LOGIN_LINE}\n\n{DIFFERENT_EMAILS_NOTE}"
    )


def test_requester_emails_same_ignoring_case():
    """Test that emails differing only in case count as the same."""
    text = requester_emails(contact_email="Doe@Home.org", ls_login_email="doe@home.org")
    assert text == (
        "Contact email for this request: Doe@Home.org\n"
        f"{LS_LOGIN_LINE}\n\n{SAME_EMAILS_NOTE}"
    )


def test_requester_emails_without_contact_email():
    """Test that only the LS Login email is shown without a contact email."""
    assert requester_emails(contact_email=None, ls_login_email="doe@home.org") == (
        LS_LOGIN_LINE
    )
