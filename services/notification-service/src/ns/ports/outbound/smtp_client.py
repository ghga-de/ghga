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
"""Contains the smtp client port"""

from abc import ABC, abstractmethod
from email.message import EmailMessage


class SmtpClientPort(ABC):
    """Abstract description of an SMTP client that can send email"""

    class ConnectionAttemptError(RuntimeError):
        """Raised when the attempt to reach the SMTP server times out or is blocked."""

        def __init__(self):
            message = "Attempt to connect to the SMTP server failed."
            super().__init__(message)

    class ServerPingError(RuntimeError):
        """To be raised when testing the connection fails"""

        def __init__(self):
            message = "Did not receive 250 status from connection test check."
            super().__init__(message)

    class FailedLoginError(RuntimeError):
        """Raised when we fail to log in"""

        def __init__(self):
            message = "Failed to log in."
            super().__init__(message)

    class GeneralSmtpException(Exception):
        """Raised by other errors (not failed connection or failed login)"""

        def __init__(self, error_info: str):
            message = (
                f"Encountered an issue while attempting to send email: {error_info}"
            )
            super().__init__(message)

    @abstractmethod
    def send_email_message(self, message: EmailMessage):
        """Sends an email message"""
        ...
