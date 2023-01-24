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
"""Handling seesion initialization for requests"""

import requests
from requests.adapters import HTTPAdapter, Retry


class RequestsSession:
    """Helper clas to make max_retries user configurable"""

    session: requests.Session

    @classmethod
    def configure(cls, max_retries: int):
        """Configure session with exponential backoff retry"""
        with requests.session() as session:
            # can't be negative - should we log this?
            max_retries = max(0, max_retries)

            retries = Retry(
                total=max_retries,
                backoff_factor=2,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retries)

            session.mount("http://", adapter=adapter)
            session.mount("https://", adapter=adapter)

            cls.session = session

    @classmethod
    def get(cls, *args, **kwargs):
        """Delegate to session method"""
        return cls.session.get(*args, **kwargs)

    @classmethod
    def patch(cls, *args, **kwargs):
        """Delegate to session method"""
        return cls.session.patch(*args, **kwargs)

    @classmethod
    def post(cls, *args, **kwargs):
        """Delegate to session method"""
        return cls.session.post(*args, **kwargs)

    @classmethod
    def put(cls, *args, **kwargs):
        """Delegate to session method"""
        return cls.session.put(*args, **kwargs)
