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

"""Tests to verify functionality of kafka event consumer"""

import pytest
from ghga_event_schemas import pydantic_ as event_schemas

from mass.core import models
from tests.fixtures.joint import JointFixture


@pytest.mark.parametrize(
    "resource_id,is_insert",
    [
        ("added-resource", True),  # this is a new ID
        ("1HotelAlpha-id", False),  # this ID exists in the test data already
    ],
)
@pytest.mark.asyncio
async def test_resource_upsert(
    joint_fixture: JointFixture, resource_id: str, is_insert: bool
):
    """Try upserting with no pre-existing resource with matching ID (i.e. insert)"""
    query_handler = await joint_fixture.container.query_handler()

    # get all the documents in the collection
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )
    assert results_all.count > 0

    # define content of resource
    content = {
        "has_object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
        "field1": "something",
        "category": "test object",
    }

    # define a resource to be upserted
    resource = models.Resource(
        id_=resource_id,
        content=content,
    )

    # put together event payload
    payload = event_schemas.SearchableResource(
        accession=resource_id,
        class_name="DatasetEmbedded",
        content=content,
    ).model_dump()

    # publish the event
    await joint_fixture.kafka.publish_event(
        payload=payload,
        type_=joint_fixture.config.resource_upsertion_event_type,
        topic=joint_fixture.config.resource_change_event_topic,
        key=f"dataset_embedded_{resource_id}",
    )

    # consume the event
    consumer = await joint_fixture.container.event_subscriber()
    await consumer.run(forever=False)

    # verify that the resource was added
    updated_resources = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )
    if is_insert:
        assert updated_resources.count - results_all.count == 1
    else:
        assert updated_resources.count == results_all.count

    assert resource in updated_resources.hits
    assert resource not in results_all.hits


@pytest.mark.asyncio
async def test_resource_delete(joint_fixture: JointFixture):
    """Test resource deletion via event consumption"""
    query_handler = await joint_fixture.container.query_handler()

    # get all the documents in the collection
    targeted_initial_results = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query='"1HotelAlpha-id"',
        filters=[],
    )
    assert targeted_initial_results.count == 1
    assert targeted_initial_results.hits[0].id_ == "1HotelAlpha-id"

    resource_info = event_schemas.SearchableResourceInfo(
        accession="1HotelAlpha-id", class_name="DatasetEmbedded"
    )

    await joint_fixture.kafka.publish_event(
        payload=resource_info.model_dump(),
        type_=joint_fixture.config.resource_deletion_event_type,
        topic=joint_fixture.config.resource_change_event_topic,
        key=f"dataset_embedded_{resource_info.accession}",
    )

    # consume the event
    consumer = await joint_fixture.container.event_subscriber()
    await consumer.run(forever=False)

    # get all the documents in the collection
    results_post_delete = await query_handler.handle_query(
        class_name="DatasetEmbedded", query='"1HotelAlpha-id"', filters=[]
    )

    assert results_post_delete.count == 0
