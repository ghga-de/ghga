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

"""Integration tests that incorporate multiple components at once.

There are two made-up services, the User File Service (UFS) and the File
Storage Service (FSS). There are also three topics: notifications, user-events,
and graph-updates. Both the UFS and FSS subscribe to the user-events, but only the UFS
subscribes to the notifications topic and only the FSS subscribes to the graph updates.
"""
