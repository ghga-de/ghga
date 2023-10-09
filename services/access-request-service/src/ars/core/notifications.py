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

"""The content of all notification and confirmation emails."""

from typing import NamedTuple

__all__ = [
    "Notification",
    "REQUEST_CREATED_NOTIFICATION",
    "REQUEST_CREATED_CONFIRMATION",
    "REQUEST_ALLOWED_NOTIFICATION",
    "REQUEST_ALLOWED_CONFIRMATION",
    "REQUEST_DENIED_NOTIFICATION",
    "REQUEST_DENIED_CONFIRMATION",
]


class Notification(NamedTuple):
    """A notification with a subject and a body text."""

    subject: str
    text: str


# The subject and text for the various notification emails.
# The attributes of the request can be interpolated.


REQUEST_CREATED_NOTIFICATION = Notification(
    "Your data download access request has been registered",
    """
Your request to download the dataset {dataset_id} has been registered.

You should be contacted by one of our data stewards in the next three workdays.
""",
)

REQUEST_CREATED_CONFIRMATION = Notification(
    "A data download access request has been created",
    """
{full_user_name} requested to download the dataset {dataset_id}.

The specified contact email address is: {email}
""",
)

REQUEST_ALLOWED_NOTIFICATION = Notification(
    "Your data download access request has been accepted",
    """
We are glad to inform you that your request to download the dataset
{dataset_id} has been accepted.

You can now start download the dataset as explained in the GHGA Data Portal.
""",
)

REQUEST_ALLOWED_CONFIRMATION = Notification(
    "Data download access has been allowed",
    """
The request by {full_user_name} to download the dataset
{dataset_id} has now been registered as allowed
and the access has been granted.
""",
)

REQUEST_DENIED_NOTIFICATION = Notification(
    "Your data download access request has been rejected",
    """
Unfortunately, your request to download the dataset
{dataset_id} has been rejected.

Please contact our help desk for information about this decision.
""",
)

REQUEST_DENIED_CONFIRMATION = Notification(
    "Data download access has been rejected",
    """
The request by {full_user_name} to download the dataset
{dataset_id} has now been registered as rejected
and the access has not been granted.
""",
)
