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
"""Contains a limited test server and testing functionality for local email verification."""

from contextlib import asynccontextmanager
from email import message_from_bytes
from email.message import EmailMessage

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import AuthResult, Envelope

from ns.config import Config


class Authenticator:
    """Basic authenticator so we can test error handling for failed authentication"""

    def __init__(self, user: str | None, password: str | None):
        self._user = user
        self._password = password

    def __call__(self, server, session, envelope, mechanism, auth_data):
        """Authenticate the credentials"""
        login = str(auth_data.login, encoding="utf-8")
        password = str(auth_data.password, encoding="utf-8")

        authenticated = login == self._user and password == self._password

        return AuthResult(success=authenticated, handled=False)


class CustomHandler(Sink):
    """Single use handler"""

    def __init__(self):
        self.email_received: Envelope
        super().__init__()

    async def handle_DATA(self, server, session, envelope):  # noqa: N802
        """Handler function for email message which closes controller upon use"""
        self.email_received = envelope

        return "250 Ok"


def check_emails(received: Envelope, expected: EmailMessage):
    """Compares two emails"""
    message_received = message_from_bytes(received.content)  # type: ignore
    assert message_received["To"] == expected["To"]
    assert message_received["Cc"] == expected["Cc"]
    assert message_received["From"] == expected["From"]
    assert message_received["Subject"] == expected["Subject"]
    assert message_received.preamble == expected.preamble
    assert (
        message_received.get_content_disposition() == expected.get_content_disposition()
    )
    assert expected.is_multipart() == message_received.is_multipart()
    expected_payload = expected.get_payload()
    received_payload = message_received.get_payload()
    # I don't think we'll have an issue with non-unique content types.
    # If we do, you could look for something like the content-id as a UID
    for part in expected_payload:
        content_type = part.get_content_type()  # type: ignore
        for corresponding in received_payload:
            if corresponding.get_content_type() == content_type:  # type: ignore
                assert part.as_bytes() == corresponding.as_bytes()  # type: ignore


class EmailRecorder:
    """Listens for one email"""

    def __init__(self, *, expected_email: EmailMessage, controller: Controller):
        self._expected_email = expected_email
        self._controller = controller

    async def __aenter__(self):
        """Async context manager entry method"""
        try:
            self._controller.start()

        except RuntimeError:
            if self._controller.loop.is_running():
                self._controller.stop()
            raise

    async def __aexit__(self, *args):
        """Async context manager exit method"""
        if self._controller.loop.is_running():
            self._controller.stop()


class DummyServer:
    """Test server for making sure emails are received as intended"""

    def __init__(self, *, config: Config):
        """Assign config"""
        self._config = config
        auth = self._config.smtp_auth
        self.login = auth.username if auth else ""
        self.password = auth.password.get_secret_value() if auth else ""

    def _record_email(
        self, *, expected_email: EmailMessage, controller: Controller
    ) -> EmailRecorder:
        """Returns an async context manager with custom controller/handler"""
        return EmailRecorder(expected_email=expected_email, controller=controller)

    @asynccontextmanager
    async def expect_email(self, expected_email: EmailMessage):
        """Yields an async context manager with a single-use SMTP message handler,
        and compares the received message envelope with the original EmailMessage
        """
        handler = CustomHandler()
        controller = Controller(
            handler,
            self._config.smtp_host,
            self._config.smtp_port,
            auth_require_tls=False,
            authenticator=Authenticator(self.login, self.password),
        )

        async with self._record_email(
            expected_email=expected_email, controller=controller
        ) as email_recorder:
            yield email_recorder

        check_emails(received=handler.email_received, expected=expected_email)
        if controller.loop.is_running():
            controller.stop()
