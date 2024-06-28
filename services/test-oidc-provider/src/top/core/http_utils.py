# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""HTTP Utilities"""

from fastapi import Request

__all__ = ["get_original_url"]


def get_original_url(request: Request) -> str:
    """Get the original URL used for the request."""
    headers = request.headers
    original_path = headers.get("x-forwarded-path") or headers.get(
        "x-envoy-original-path"
    )
    if original_path:
        # construct the URL using header values
        original_host = (
            headers.get("x-forwarded-host")
            or headers.get("x-envoy-original-host")
            or headers.get("host")
            or request.url.netloc
        )
        original_scheme = (
            headers.get("x-forwarded-proto")
            or headers.get("x-envoy-original-proto")
            or request.url.scheme
        )
        original_url = f"{original_scheme}://{original_host}{original_path}"
    else:
        # get the URL without query param from the request
        original_url = str(request.url.replace(query=None))
    return original_url
