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
"""Contains the concrete implementation of a NotifierPort"""
import logging
from email.message import EmailMessage
from enum import Enum
from string import Template

from ghga_event_schemas import pydantic_ as event_schemas
from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings

from ns.ports.inbound.notifier import NotifierPort
from ns.ports.outbound.smtp_client import SmtpClientPort

log = logging.getLogger(__name__)


class EmailTemplateType(str, Enum):
    """Enumeration for the types of email template."""

    PLAINTEXT = "plaintext"
    HTML = "html"


class NotifierConfig(BaseSettings):
    """Config details for the notifier"""

    plaintext_email_template: str = Field(
        ..., description="The plaintext template to use for email notifications"
    )
    html_email_template: str = Field(
        ..., description="The HTML template to use for email notifications"
    )
    from_address: EmailStr = Field(..., description="The sender's address.")


class Notifier(NotifierPort):
    """Implementation of the Notifier Port"""

    def __init__(self, *, config: NotifierConfig, smtp_client: SmtpClientPort):
        """Initialize the Notifier with configuration and smtp client"""
        self._config = config
        self._smtp_client = smtp_client

    async def send_notification(self, *, notification: event_schemas.Notification):
        """Sends notifications based on the channel info provided (e.g. email addresses)"""
        if len(notification.recipient_email) > 0:
            message = self._construct_email(notification=notification)
            self._smtp_client.send_email_message(message)

    def _construct_email(
        self, *, notification: event_schemas.Notification
    ) -> EmailMessage:
        """Constructs an EmailMessage object from the contents of an email notification event"""
        message = EmailMessage()
        message["To"] = notification.recipient_email
        message["Cc"] = notification.email_cc
        message["Bcc"] = notification.email_bcc
        message["Subject"] = notification.subject
        message["From"] = self._config.from_address

        payload_as_dict = notification.model_dump()

        # create plaintext html with template
        plaintext_template = Template(self._config.plaintext_email_template)
        try:
            plaintext_email = plaintext_template.substitute(payload_as_dict)
        except KeyError as err:
            template_var_error = self.VariableNotSuppliedError(variable=err.args[0])
            log.critical(template_var_error, extra={"variable": err.args[0]})
            raise template_var_error from err
        except ValueError as err:
            template_format_error = self.BadTemplateFormat(
                template_type=EmailTemplateType.PLAINTEXT, problem=err.args[0]
            )
            log.critical(
                template_format_error,
                extra={
                    "template_type": EmailTemplateType.PLAINTEXT,
                    "problem": err.args[0],
                },
            )
            raise template_format_error from err

        message.set_content(plaintext_email)

        # create html version of email, replacing variables of $var format
        html_template = Template(self._config.html_email_template)

        try:
            html_email = html_template.substitute(payload_as_dict)
        except KeyError as err:
            template_var_error = self.VariableNotSuppliedError(variable=err.args[0])
            log.critical(template_var_error, extra={"variable": err.args[0]})
            raise template_var_error from err
        except ValueError as err:
            template_format_error = self.BadTemplateFormat(
                template_type=EmailTemplateType.HTML, problem=err.args[0]
            )
            log.critical(
                template_format_error,
                extra={"template_type": EmailTemplateType.HTML, "problem": err.args[0]},
            )
            raise template_format_error from err

        # add the html version to the EmailMessage object
        message.add_alternative(html_email, subtype=EmailTemplateType.HTML)

        return message
