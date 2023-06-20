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

"""Data that are used in unit tests"""

EXPECTED_CONVERSION = {
    "books": [
        {
            "writer_name": "Albert Camus",
            "book_name": "The Plague",
            "isbn": "9780679720218",
        },
        {
            "writer_name": "George Orwell",
            "book_name": "1984",
            "isbn": "9783548234106",
        },
    ],
    "publisher": [
        {
            "isbn": "9780679720218",
            "publisher_names": ["Hamish Hamilton", "Stephen King"],
            "attributes": [
                {"key": "page", "value": "100"},
                {"key": "cover", "value": "paperback"},
            ],
        },
        {"isbn": "9783548234106", "publisher_names": ["Secker and Warburg"]},
    ],
}
