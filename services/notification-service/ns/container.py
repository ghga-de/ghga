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
"""Contains dependency injection setup"""
from hexkit.inject import ContainerBase, get_configurator, get_constructor
from hexkit.providers.akafka.provider import KafkaEventSubscriber

from ns.adapters.inbound.akafka import EventSubTranslator
from ns.config import Config
from ns.core.notifier import Notifier


class Container(ContainerBase):
    """Dependency-Injection Container"""

    config = get_configurator(Config)

    # domain components
    notifier = get_constructor(Notifier, config=config)

    # inbound translators
    event_sub_translator = get_constructor(EventSubTranslator, config=config)

    # inbound providers
    kafka_event_subscriber = get_constructor(
        KafkaEventSubscriber, config=config, translator=event_sub_translator
    )
