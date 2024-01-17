# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
import smtplib
import ssl
from email.message import EmailMessage

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from ns.ports.outbound.smtp_client import SmtpClientPort

log = logging.getLogger(__name__)


class SmtpClientConfig(BaseSettings):
    """Configuration details for the SmtpClient"""

    smtp_host: str = Field(..., description="The mail server host to connect to")
    smtp_port: int = Field(..., description="The port for the mail server connection")
    login_user: str = Field(..., description="The login username or email")
    login_password: SecretStr = Field(..., description="The login password")
    use_starttls: bool = Field(
        default=True, description="Boolean flag indicating the use of STARTTLS"
    )


class SmtpClient(SmtpClientPort):
    """Concrete implementation of an SmtpClientPort"""

    def __init__(self, *, config: SmtpClientConfig):
        """Assign config, which should contain all needed info"""
        self._config = config

    def send_email_message(self, message: EmailMessage):
        """Send an email message.

        Creates an ssl security context if configured, then log in with the configured
        credentials and send the provided email message.
        """
        try:
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                if self._config.use_starttls:
                    # create ssl security context per Python's Security considerations
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                try:
                    server.login(
                        self._config.login_user,
                        self._config.login_password.get_secret_value(),
                    )
                except smtplib.SMTPAuthenticationError as err:
                    login_error = self.FailedLoginError()
                    log.critical(login_error)
                    raise login_error from err

                # check for a connection
                if server.noop()[0] != 250:
                    connection_error = self.ConnectionError()
                    log.critical(connection_error)
                    raise connection_error

                server.send_message(msg=message)
        except smtplib.SMTPException as exc:
            error = self.GeneralSmtpException(error_info=exc.args[0])
            log.error(error, extra={"error_info": exc.args[0]})
            raise error from exc
