# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

"""Data that is expected as output in unit tests"""

from arcticfreeze import FrozenDict
from schemapack._internals.spec.datapack import ResourceRelation
from schemapack.spec.datapack import DataPack, Resource

EXPECTED_CONVERSION_DATAPACK = DataPack(
    datapack="0.3.0",
    resources=FrozenDict(
        {
            "books": FrozenDict(
                {
                    "Albert Camus": Resource(
                        content=FrozenDict(
                            {
                                "book_name": "The Plague",
                                "genre": ("PHILOSOPHICAL_NOVEL", "ABSURDIST_NOVEL"),
                                "set_in": "FRENCH_ALGERIA",
                            }
                        ),
                        relations=FrozenDict(
                            {
                                "isbn": ResourceRelation(
                                    targetClass="publisher",
                                    targetResources="9780679720218",
                                )
                            }
                        ),
                    ),
                    "George Orwell": Resource(
                        content=FrozenDict(
                            {
                                "book_name": "1984",
                                "genre": ("DYSTOPIAN_NOVEL", "CAUTIONARY_TALE"),
                                "set_in": "UNITED_KINGDOM",
                            }
                        ),
                        relations=FrozenDict(
                            {
                                "isbn": ResourceRelation(
                                    targetClass="publisher",
                                    targetResources="9783548234106",
                                )
                            }
                        ),
                    ),
                }
            ),
            "publisher": FrozenDict(
                {
                    "9780679720218": Resource(
                        content=FrozenDict(
                            {
                                "publisher_names": ("Hamish Hamilton", "Stephen King"),
                                "attributes": (
                                    FrozenDict({"key": "page", "value": "100"}),
                                    FrozenDict({"key": "cover", "value": "paperback"}),
                                ),
                            }
                        ),
                        relations=FrozenDict({}),
                    ),
                    "9783548234106": Resource(
                        content=FrozenDict(
                            {"publisher_names": ("Secker and Warburg",)}
                        ),
                        relations=FrozenDict({}),
                    ),
                }
            ),
        }
    ),
    rootResource=None,
    rootClass=None,
)

EXPECTED_CONVERSION_JSON = {
    "datapack": "0.3.0",
    "resources": {
        "books": {
            "Albert Camus": {
                "content": {
                    "book_name": "The Plague",
                    "genre": [
                        "PHILOSOPHICAL_NOVEL",
                        "ABSURDIST_NOVEL",
                    ],
                    "set_in": "FRENCH_ALGERIA",
                },
                "relations": {
                    "isbn": {
                        "targetClass": "publisher",
                        "targetResources": "9780679720218",
                    },
                },
            },
            "George Orwell": {
                "content": {
                    "book_name": "1984",
                    "genre": [
                        "DYSTOPIAN_NOVEL",
                        "CAUTIONARY_TALE",
                    ],
                    "set_in": "UNITED_KINGDOM",
                },
                "relations": {
                    "isbn": {
                        "targetClass": "publisher",
                        "targetResources": "9783548234106",
                    },
                },
            },
        },
        "publisher": {
            "9780679720218": {
                "content": {
                    "attributes": [
                        {
                            "key": "page",
                            "value": "100",
                        },
                        {
                            "key": "cover",
                            "value": "paperback",
                        },
                    ],
                    "publisher_names": [
                        "Hamish Hamilton",
                        "Stephen King",
                    ],
                }
            },
            "9783548234106": {
                "content": {
                    "publisher_names": [
                        "Secker and Warburg",
                    ],
                },
            },
        },
    },
}
