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

"""Fixture for testing code that uses the MongoDbDaoFactory provider."""

from collections.abc import Mapping
from time import sleep
from typing import Any

from pymongo import MongoClient
from pytest import fixture

from fixtures.config import Config
from fixtures.http_client import HttpClient
from fixtures.state_manager import StateManager

__all__ = [
    "MongoClient",
    "MongoFixture",
    "mongo_fixture",
]

TIMEOUT = 10  # timeout for database operations in seconds
INTERVAL = 0.1  # interval for retrying database operations in seconds
EXTENDED_ID_FIELDS = ["_id", "user_id", "iva_id"]


class MongoFixture(StateManager):
    """Fixture for managing MongoDB resources."""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    config: Config

    def extended_mapping(self, document: dict[str, Any]) -> dict[str, Any]:
        """Convert *_id fields to MongoDB extended JSON format"""
        doc_copy = document.copy()
        for k, v in document.items():
            if k in EXTENDED_ID_FIELDS and isinstance(v, str):
                doc_copy[k] = {"$uuid": v}
        return doc_copy

    @property
    def service_db_names(self) -> list[str]:
        return self.config.service_db_names  # pylint: disable=no-member

    def empty_databases(
        self,
        db_names: str | list[str] | None = None,
        collection_names: str | list[str] | None = None,
    ) -> None:
        """Delete all or some documents in the given namespace(s)"""
        if db_names is None:
            db_names = self.service_db_names

        if isinstance(db_names, str):
            db_names = [db_names]

        if isinstance(collection_names, str):
            collection_names = [collection_names]
        else:
            collection_names = collection_names or ["*"]

        for db_name in db_names:
            for collection_name in collection_names:
                self.remove_documents(db_name=db_name, collection_name=collection_name)

    def find_document(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any] | None = None,
        extend_mapping: bool = True,
    ) -> dict[str, Any] | None:
        documents = self.find_documents(
            db_name=db_name,
            collection_name=collection_name,
            query=query,
            extend_mapping=extend_mapping,
        )
        return documents[0] if documents else None

    def find_documents(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any] | None = None,
        sloppy: bool = False,
        extend_mapping: bool = True,
    ) -> list[dict[str, Any]]:
        """Return one document from the given collection matching the given filter."""
        url = f"{self.config.sms_url}/documents/{db_name}.{collection_name}"
        if query:
            if db_name != "tb" and extend_mapping:
                query = self.extended_mapping(query)  # type: ignore
            query = self.stringify_query_params(query)
        response = self.http.get(url, headers=self.auth_headers, params=query)
        status_code = response.status_code
        if status_code == 200:
            return response.json()
        if status_code == 404 and sloppy:
            return []  # treat non-existing collections as being empty
        assert False, (
            f"Failed to retrieve documents from {db_name}.{collection_name}"
            f" with status code {status_code}: {response.text}"
        )

    def wait_for_document(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any],
        timeout: float = TIMEOUT,
        interval: float = INTERVAL,
        extend_mapping: bool = True,
    ) -> dict[str, Any] | None:
        documents = self.wait_for_documents(
            db_name=db_name,
            collection_name=collection_name,
            query=query,
            number=1,
            timeout=timeout,
            interval=interval,
            extend_mapping=extend_mapping,
        )
        return documents[0] if documents else None

    def wait_for_documents(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any],
        number: int = 1,
        timeout: float = TIMEOUT,
        interval: float = INTERVAL,
        extend_mapping: bool = True,
    ) -> list[dict[str, Any]] | None:
        """Wait for a number of documents.

        Waits for the given number of documents from the given collection matching
        the given filter to appear in the database. If they do not appear in the
        given timeout (in seconds), then a value of None is returned. Otherwise, the
        list of these documents will be returned (can be also larger than requested).
        """
        slept: float = 0
        while slept < timeout:
            documents = self.find_documents(
                db_name, collection_name, query, True, extend_mapping
            )
            if len(documents) >= number:
                return documents
            sleep(interval)
            slept += interval
        return None

    def upsert_document(
        self,
        db_name: str,
        collection_name: str,
        document: dict[str, Any],
        extend_mapping: bool = True,
    ):
        """Replace one document in the given collection.

        Set `extend_mapping=False` when the document already carries extended-JSON
        values or when the `_id` is not a UUID.
        """
        if db_name != "tb" and extend_mapping:
            document = self.extended_mapping(document)
        url = f"{self.config.sms_url}/documents/{db_name}.{collection_name}"
        data = {"documents": document, "id_field": "_id"}
        response = self.http.put(url, headers=self.auth_headers, json=data)
        assert response.status_code == 204, (
            f"Failed to replace document: {response.text}"
        )

    def remove_documents(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any] | None = None,
    ):
        """Remove one document in the given collection with the given document."""
        # Previous remove method uses regex so it was possible to delete multiple by keyword, with sms it's not possible
        url = f"{self.config.sms_url}/documents/{db_name}.{collection_name}"
        if query:
            query = self.stringify_query_params(query)
        response = self.http.delete(url, headers=self.auth_headers, params=query)
        assert response.status_code == 204, (
            f"Failed to delete document: {response.text}"
        )

    def wait_for_removal(
        self,
        db_name: str,
        collection_name: str,
        query: Mapping[str, Any],
        timeout: float = TIMEOUT,
        interval: float = INTERVAL,
        extend_mapping: bool = True,
    ) -> bool:
        """Wait until no document matches the given query.

        The counterpart to `wait_for_documents`: polls until `find_document`
        finds nothing for the given filter and returns True, or returns False if
        a match still remains at timeout. Useful for event-driven deletions that
        propagate to a collection asynchronously.
        """
        slept: float = 0
        while slept < timeout:
            if (
                self.find_document(db_name, collection_name, query, extend_mapping)
                is None
            ):
                return True
            sleep(interval)
            slept += interval
        return False


@fixture(name="mongo", scope="session")
def mongo_fixture(config: Config, http: HttpClient) -> MongoFixture:
    """Pytest fixture for tests depending on the Mongo database."""
    return MongoFixture(config=config, http=http)
