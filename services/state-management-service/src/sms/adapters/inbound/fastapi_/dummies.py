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
"""A collection of dependency dummies that are used in view definitions but need to be
replaced at runtime by actual dependencies.
"""

from typing import Annotated

from fastapi import Depends
from ghga_service_commons.api.di import DependencyDummy

from sms.config import Config
from sms.ports.inbound.docs_handler import DocsHandlerPort
from sms.ports.inbound.events_handler import EventsHandlerPort
from sms.ports.inbound.objects_handler import ObjectsHandlerPort
from sms.ports.inbound.secrets_handler import SecretsHandlerPort

config_dummy = DependencyDummy("config_dummy")
docs_handler_port = DependencyDummy("docs_handler_port")
objects_handler_port = DependencyDummy("objects_handler_port")
events_handler_port = DependencyDummy("events_handler_port")
secrets_handler_port = DependencyDummy("secrets_handler_port")

ConfigDummy = Annotated[Config, Depends(config_dummy)]
DocsHandlerPortDummy = Annotated[DocsHandlerPort, Depends(docs_handler_port)]
ObjectsHandlerPortDummy = Annotated[ObjectsHandlerPort, Depends(objects_handler_port)]
EventsHandlerPortDummy = Annotated[EventsHandlerPort, Depends(events_handler_port)]
SecretsHandlerPortDummy = Annotated[SecretsHandlerPort, Depends(secrets_handler_port)]
