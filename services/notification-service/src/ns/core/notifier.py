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
from contextlib import suppress
from email.message import EmailMessage
from enum import Enum
from hashlib import sha256
from string import Template

from ghga_event_schemas import pydantic_ as event_schemas
from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings

from ns.core import models
from ns.ports.inbound.notifier import NotifierPort
from ns.ports.outbound.dao import NotificationRecordDaoPort, ResourceNotFoundError
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

    def __init__(
        self,
        *,
        config: NotifierConfig,
        smtp_client: SmtpClientPort,
        notification_record_dao: NotificationRecordDaoPort,
    ):
        """Initialize the Notifier with configuration and smtp client"""
        self._config = config
        self._smtp_client = smtp_client
        self._notification_record_dao = notification_record_dao

    def _create_notification_record(
        self, *, notification: event_schemas.Notification
    ) -> models.NotificationRecord:
        """Creates a notification record from a notification event"""
        hash_sum = sha256(notification.model_dump_json().encode("utf-8")).hexdigest()
        return models.NotificationRecord(hash_sum=hash_sum, sent=False)

    async def _has_been_sent(self, *, hash_sum: str) -> bool:
        """Check whether the notification has been sent already.

        Returns:
        - `False` if the notification **has not** been sent yet.
        - `True` if the notification **has** already been sent.
        """
        with suppress(ResourceNotFoundError):
            record = await self._notification_record_dao.get_by_id(id_=hash_sum)
            return record.sent
        return False

    async def _register_new_notification(
        self, *, notification_record: models.NotificationRecord
    ):
        """Registers a new notification in the database"""
        await self._notification_record_dao.upsert(dto=notification_record)

    async def send_notification(self, *, notification: event_schemas.Notification):
        """Sends notifications based on the channel info provided (e.g. email addresses)"""
        # Generate sha-256 hash of the notification payload
        notification_record = self._create_notification_record(
            notification=notification
        )

        # Abort if the notification has been sent already
        if await self._has_been_sent(hash_sum=notification_record.hash_sum):
            log.info("Notification already sent, skipping.")
            return

        # Add the notification to the database (with sent=False)
        await self._register_new_notification(notification_record=notification_record)

        message = self._construct_email(notification=notification)
        self._smtp_client.send_email_message(message)

        # update the notification record to show that the notification has been sent.
        notification_record.sent = True
        await self._notification_record_dao.update(dto=notification_record)

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
