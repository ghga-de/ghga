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
"""Contains the sms client port"""

from abc import ABC, abstractmethod


class SmsClientPort(ABC):
    """Abstract description of an SMS client that can send messages"""

    class SystemError(RuntimeError):
        """Raised when SMS gateway behaves unexpectedly"""

        def __init__(self):
            message = "Gateway system error occurred."
            super().__init__(message)

    class RequestError(RuntimeError):
        """Raised when request is malformed or resource is not found"""

        def __init__(self):
            message = "Request is malformed or resource is not found."
            super().__init__(message)

    class AccountError(RuntimeError):
        """Raised when authentication or authorization fails"""

        def __init__(self):
            message = "Authentication failed or account related issue occurred."
            super().__init__(message)

    class GeneralSmsException(Exception):
        """Raised by other errors"""

        def __init__(self, error_info: str):
            message = f"Encountered an issue while attempting to send SMS: {error_info}"
            super().__init__(message)

    @abstractmethod
    def send_sms_message(self, *, phone: str, text: str):
        """Sends an SMS message"""
        ...
