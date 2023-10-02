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

"""A collection of client-side exceptions."""

from ghga_service_commons.httpyexpect.base_exception import HttpyExpectError


class UnexpectedError(HttpyExpectError):
    """Error for HTTP Error/ExceptionMapping mismatch.

    Thrown when an HTTP error (originating from the server-side) could not be mapped
    using an ExceptionMapping (see the `mapping` module).
    (The HTTP error is, however, following the HttpyExceptionBody model as defined in
    the `httpyexpect.models` module.).
    """

    def __init__(
        self, *, status_code: int, exception_id: str, description: str, data: dict
    ):
        """Initialize the error with the required metadata.

        Args:
            status_code:
                The response code of the HTTP response.
            exception_id:
                An identifier used to distinguish between different exception causes in
                a preferably fine-grained fashion. The distinction between causes should
                be made from the perspective of the server/service raising the exception
                (and not from the client perspective). Needs to be camel case formatted
                and 3-40 character in length.
            description:
                A human readable message to the client explaining the cause of the
                exception.
            data:
                An object containing further details on the exception cause in a machine
                readable way.  All exceptions with the same exception_id should use the
                same set of properties here. This object may be empty (in case no data
                is required)
        """
        self.status_code = status_code
        self.exception_id = exception_id
        self.description = description
        self.data = data

        message = (
            f"Unexpected error with ID {self.exception_id} and status code"
            + f"{self.status_code}: {self.description}"
        )
        super().__init__(message)


class UnstructuredError(HttpyExpectError):
    """Error for bad error response model.

    Thrown when an HTTP error (originating from the server-side) did not comply with
    the HttpyExceptionBody model as defined in the `httpyexpect.models` module.
    """

    def __init__(self, *, status_code: int, body: str):
        """Initialize the error with the required metadata.

        Args:
            status_code:
                The response code of the HTTP response.
            body:
                The string representation of the body shipped with the response.
        """
        self.status_code = status_code
        self.body = body

        message = (
            f"An error response with status code {self.status_code} was obtained of"
            + f" which the body did not comply with the expected schema: {self.body}"
        )
        super().__init__(message)
