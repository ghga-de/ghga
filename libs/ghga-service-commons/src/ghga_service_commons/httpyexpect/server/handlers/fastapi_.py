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

"""Handling exceptions in FastAPI. FastAPI has to be installed."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = ["configure_exception_handler"]


def configure_exception_handler(app: FastAPI) -> None:
    """Configure a FastAPI app to handle httpyexpect's HttpExceptions.

    Args:
        app: The FastAPI to attach the exception handler to.
    """

    @app.exception_handler(HttpException)
    def httpy_exception_handler(
        request: Request,
        # (The above is required by the corresponding FastAPI interface but not used here)
        exc: HttpException,
    ) -> JSONResponse:
        """Attach a custom exception handler to the FastAPI app.

        The custom exception handler translates httpyexpect's HttpExceptions
        into a FastAPI JSONResponse.
        """
        return JSONResponse(status_code=exc.status_code, content=exc.body.model_dump())

    @app.exception_handler(500)
    def unhandled_exception_handler(
        request: Request,
        # (The above is required by the corresponding FastAPI interface but not used here)
        exc: HttpException,
    ) -> JSONResponse:
        """Attach a custom 500 exception handler to the FastAPI app.

        This exception handler should properly wrap unhandled exceptions so they only
        propagate a generic message instead of carrying the actual exception message.
        """
        return JSONResponse(
            status_code=500, content={"message": "Internal Server Error."}
        )
