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

"""Logic for handling submission event including source events and submission-scoped
artifacts.
"""


from pydantic import Field
from pydantic_settings import BaseSettings


class SourceEventConfig(BaseSettings):
    """Config parameters and their defaults."""

    source_event_topic: str = Field(
        "source_events",
        description="Name of the topic to which source events are published.",
    )
    source_event_type: str = Field(
        "source_event", description="Name of the event type for source events."
    )
