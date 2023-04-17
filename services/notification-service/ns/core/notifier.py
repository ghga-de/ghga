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

from email.message import EmailMessage
from string import Template

from ghga_event_schemas import pydantic_ as event_schemas

from ns.config import Config
from ns.ports.inbound.notifier import NotifierPort


class Notifier(NotifierPort):
    """Implementation of the Notifier Port"""

    def __init__(self, *, config: Config):
        """Initialize the Notifier with configured host, port, and so on"""
        self._config = config

    async def send_notification(self, *, notification: event_schemas.Notification):
        """Sends notifications based on the channel info provided (e.g. email addresses)"""
        raise NotImplementedError

    def _construct_email(
        self, *, notification: event_schemas.Notification
    ) -> EmailMessage:
        """Constructs an EmailMessage object from the contents of an email notification event"""
        message = EmailMessage()
        message["To"] = notification.recipient_email
        message["Cc"] = notification.email_cc
        message["Bcc"] = notification.email_bcc
        message["Subject"] = notification.subject

        payload_as_dict = notification.dict()

        # create plaintext html with template
        plaintext_template = Template(self._config.plaintext_email_template)
        try:
            plaintext_email = plaintext_template.substitute(payload_as_dict)
        except KeyError as err:
            raise self.VariableNotSuppliedError(variable=err.args[0]) from err
        except ValueError as err:
            raise self.BadTemplateFormat(problem=err.args[0]) from err

        message.set_content(plaintext_email)

        # create html version of email, replacing variables of $var format
        html_template = Template(self._config.html_email_template)

        try:
            html_email = html_template.substitute(payload_as_dict)
        except KeyError as err:
            raise self.VariableNotSuppliedError(variable=err.args[0]) from err
        except ValueError as err:
            raise self.BadTemplateFormat(problem=err.args[0]) from err

        # add the html version to the EmailMessage object
        message.add_alternative(html_email, subtype="html")

        return message
