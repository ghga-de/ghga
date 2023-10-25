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


"""Utils for dependency injection using FastAPI."""


class DependencyDummy:
    """A placeholder for a dependency that is injected at runtime into a FastAPI app.
    To be used in view definitions with the fastapi.Depends construct:
    https://fastapi.tiangolo.com/tutorial/dependencies/
    """

    def __init__(self, label: str):
        """Initialize with a label that should describe the dependency that shall be
        injected.
        """
        self.label = label

    def __repr__(self):
        """Return a string representation of the dependency."""
        return f"DependencyDummy('{self.label}')"

    def __call__(self):
        """Should never be called. If this is called it means that this dummy has not
        been replaced with the real dependency. An error will be raised.
        """
        raise RuntimeError(
            f"The dependency dummy with label '{self.label}' was not replaced with an"
            + " actual dependency."
        )
