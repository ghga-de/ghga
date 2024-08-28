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

"""Contains the smtp client adapter"""

import logging
import ssl
from collections.abc import Generator
from contextlib import contextmanager
from email.message import EmailMessage
from smtplib import SMTP, SMTPAuthenticationError, SMTPException

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings

from ns.ports.outbound.smtp_client import SmtpClientPort

log = logging.getLogger(__name__)


class SmtpAuthConfig(BaseModel):
    """Model to encapsulate SMTP authentication details."""

    username: str = Field(default=..., description="The login username or email")
    password: SecretStr = Field(default=..., description="The login password")


class SmtpClientConfig(BaseSettings):
    """Configuration details for the SmtpClient"""

    smtp_host: str = Field(
        default=..., description="The mail server host to connect to"
    )
    smtp_port: int = Field(
        default=..., description="The port for the mail server connection"
    )
    smtp_auth: SmtpAuthConfig | None = Field(default=None, description="")
    use_starttls: bool = Field(
        default=True, description="Boolean flag indicating the use of STARTTLS"
    )


class SmtpClient(SmtpClientPort):
    """Concrete implementation of an SmtpClientPort"""

    def __init__(self, *, config: SmtpClientConfig):
        """Assign config, which should contain all needed info"""
        self._config = config

    @contextmanager
    def get_connection(self) -> Generator[SMTP, None, None]:
        """Establish a connection to the SMTP server"""
        with SMTP(self._config.smtp_host, self._config.smtp_port) as server:
            yield server

    def send_email_message(self, message: EmailMessage):
        """Send an email message.

        Creates an ssl security context if configured, then logs in with the configured
        credentials and sends the provided email message.
        In the case that username and password are `None`, authentication will not be
        performed.
        """
        try:
            with self.get_connection() as server:
                if self._config.use_starttls:
                    # create ssl security context per Python's Security considerations
                    context = ssl.create_default_context()
                    server.starttls(context=context)

                if self._config.smtp_auth:
                    username = self._config.smtp_auth.username
                    password = self._config.smtp_auth.password.get_secret_value()
                    try:
                        server.login(username, password)
                    except SMTPAuthenticationError as err:
                        login_error = self.FailedLoginError()
                        log.critical(login_error)
                        raise login_error from err

                # check for a connection
                if server.noop()[0] != 250:
                    connection_error = self.ConnectionError()
                    log.critical(connection_error)
                    raise connection_error

                server.send_message(msg=message)
        except SMTPException as exc:
            error = self.GeneralSmtpException(error_info=exc.args[0])
            log.error(error, extra={"error_info": exc.args[0]})
            raise error from exc
