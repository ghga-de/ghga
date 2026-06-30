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

"""Configurations that are expected as output in unit tests"""

from ghga_transpiler.config import ColumnMeta, SheetMeta

BOOKS_SHEET_META = SheetMeta(
    name="books",
    header_row=1,
    start_row=2,
    start_column=1,
    end_column=5,
    primary_key="writer_name",
)

BOOKS_COLUMN_META = (
    ColumnMeta(
        sheet="books",
        column="writer_name",
        multivalued=False,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=False,
        required=True,
    ),
    ColumnMeta(
        sheet="books",
        column="book_name",
        multivalued=False,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=False,
        required=True,
    ),
    ColumnMeta(
        sheet="books",
        column="isbn",
        multivalued=False,
        type="string",
        ref_class="publisher",
        ref_class_id_property="isbn",
        enum=False,
        required=True,
    ),
    ColumnMeta(
        sheet="books",
        column="genre",
        multivalued=True,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=True,
        required=True,
    ),
    ColumnMeta(
        sheet="books",
        column="set_in",
        multivalued=False,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=True,
        required=True,
    ),
)

PUBLISHER_SHEET_META = SheetMeta(
    name="publisher",
    header_row=1,
    start_row=2,
    start_column=1,
    end_column=3,
    primary_key="isbn",
)
PUBLISHER_COLUMN_META = (
    ColumnMeta(
        sheet="publisher",
        column="isbn",
        multivalued=False,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=False,
        required=True,
    ),
    ColumnMeta(
        sheet="publisher",
        column="publisher_names",
        multivalued=True,
        type="string",
        ref_class=None,
        ref_class_id_property=None,
        enum=False,
        required=True,
    ),
    ColumnMeta(
        sheet="publisher",
        column="attributes",
        multivalued=True,
        type="object",
        ref_class=None,
        ref_class_id_property=None,
        enum=False,
        required=False,
    ),
)
