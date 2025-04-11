# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import html
import json
import logging
from contextlib import suppress
from email.message import EmailMessage
from enum import Enum
from hashlib import sha256
from string import Template

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.correlation import get_correlation_id
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
        """Creates a notification record from a notification event and correlation ID."""
        correlation_id = get_correlation_id()
        notification_str = json.dumps(notification.model_dump(), sort_keys=True)
        concatenated = correlation_id + notification_str
        hash_sum = sha256(concatenated.encode("utf-8")).hexdigest()
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
        log.info("Sending notification")
        self._smtp_client.send_email_message(message)

        # update the notification record to show that the notification has been sent.
        notification_record.sent = True
        await self._notification_record_dao.update(dto=notification_record)

    def _build_email_subtype(
        self, *, template_type: EmailTemplateType, email_vars: dict[str, str]
    ):
        """Builds an email message subtype (HTML or plaintext) from a template and
        a dictionary of values.
        """
        # Escape values exposed to the email in case they've been maliciously crafted
        if template_type != EmailTemplateType.PLAINTEXT:
            for k, v in email_vars.items():
                if isinstance(v, list):
                    email_vars[k] = ", ".join(
                        [html.escape(list_element) for list_element in v]
                    )
                else:
                    email_vars[k] = html.escape(v)

        template_str = (
            self._config.plaintext_email_template
            if template_type == EmailTemplateType.PLAINTEXT
            else self._config.html_email_template
        )

        # Load the string as a python string template
        template = Template(template_str)

        # Try to substitute the values into the template
        try:
            email_subtype = template.substitute(email_vars)
        except KeyError as err:
            template_var_error = self.VariableNotSuppliedError(variable=err.args[0])
            log.critical(template_var_error, extra={"variable": err.args[0]})
            raise template_var_error from err
        except ValueError as err:
            template_format_error = self.BadTemplateFormat(
                template_type=template_type, problem=err.args[0]
            )
            log.critical(
                template_format_error,
                extra={"template_type": template_type, "problem": err.args[0]},
            )
            raise template_format_error from err
        return email_subtype

    def _construct_email(
        self, *, notification: event_schemas.Notification
    ) -> EmailMessage:
        """Constructs an EmailMessage object from the contents of an email notification event"""
        message = EmailMessage()
        message["To"] = notification.recipient_email
        if notification.email_cc:
            message["Cc"] = notification.email_cc
        if notification.email_bcc:
            message["Bcc"] = notification.email_bcc
        message["Subject"] = notification.subject
        message["From"] = self._config.from_address

        payload_as_dict = {**notification.model_dump()}

        # create plaintext html with template
        plaintext_email = self._build_email_subtype(
            template_type=EmailTemplateType.PLAINTEXT, email_vars=payload_as_dict
        )
        message.set_content(plaintext_email)

        # create html version of email, replacing variables of $var format
        html_email = self._build_email_subtype(
            template_type=EmailTemplateType.HTML, email_vars=payload_as_dict
        )

        # add the html version to the EmailMessage object
        message.add_alternative(html_email, subtype=EmailTemplateType.HTML)

        return message
