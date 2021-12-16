# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

"""Defines all database specific ORM classes (e.g. for SQLAlchemy)"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSON

from .db import Base


class ExampleObjectA(Base):
    """An example object stored in the DB"""

    __tablename__ = "visas"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    some_json_details = Column(JSON, nullable=False)


class ExampleObjectB(Base):
    """Another example object stored in the DB"""

    __tablename__ = "table_b"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, nullable=False)
