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

from nos.core.notifications import DIFFERENT_EMAILS_NOTE, requester_emails


def test_requester_emails_different():
    """Test that differing emails are both named, with an explanation."""
    text = requester_emails(
        contact_email="doe@institute.org", ls_login_email="doe@home.org"
    )
    assert text == (
        "Contact email for this request: doe@institute.org\n"
        "LS Login email address of the user: doe@home.org\n\n"
        f"{DIFFERENT_EMAILS_NOTE}"
    )


def test_requester_emails_same_ignoring_case():
    """Test that emails differing only in case are shown as one email."""
    text = requester_emails(contact_email="Doe@Home.org", ls_login_email="doe@home.org")
    assert text == "Email address of the user: Doe@Home.org"


def test_requester_emails_without_contact_email():
    """Test that the LS Login email is shown as the only email without a contact email."""
    text = requester_emails(contact_email=None, ls_login_email="doe@home.org")
    assert text == "Email address of the user: doe@home.org"
