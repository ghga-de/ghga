# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""
Basic HTTP authentication
"""

import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ...config import Config

__all__ = ["basic_auth"]


def basic_auth(app: FastAPI, config: Config):
    """Inject Basic authentication if this is configured."""
    user, pwd = config.basic_auth_user, config.basic_auth_pwd
    if not (user and pwd):
        return None
    realm = config.basic_auth_realm
    if not realm:
        return None

    required_credentials = HTTPBasicCredentials(username=user, password=pwd)
    http_basic = HTTPBasic(realm=realm)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc):
        if "WWW-Authenticate" in exc.headers:
            return PlainTextResponse(
                f"{realm}: {exc.detail}",
                status_code=exc.status_code,
                headers=exc.headers,
            )
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    async def check_basic_auth(
        passed_credentials: HTTPBasicCredentials = Depends(http_basic),
    ):
        """Check basic access authentication if username and passwort are set."""
        # checking user and password while avoiding timing attacks
        user_ok = secrets.compare_digest(
            passed_credentials.username, required_credentials.username
        )
        pwd_ok = secrets.compare_digest(
            passed_credentials.password, required_credentials.password
        )
        if not (user_ok and pwd_ok):
            www_auth = f'Basic realm="{realm}"'
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": www_auth},
            )

    return Depends(check_basic_auth)
