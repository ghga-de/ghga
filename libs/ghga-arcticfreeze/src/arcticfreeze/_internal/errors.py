# Copyright 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Exceptions raised when an object cannot be frozen."""


class FreezeError(ValueError):
    """Base class for all errors raised when an object cannot be frozen.

    It subclasses `ValueError` so that Pydantic turns it into a `ValidationError`
    when `freeze` runs inside a validator.
    """


class ConverterNotFoundError(FreezeError):
    """An exception indicating that a converter for a given type could not be found."""

    def __init__(self, *, input_type: type):
        super().__init__(
            f"No converter was found freezing an object of type {input_type}."
        )


class MaxDepthExceededError(FreezeError):
    """An exception indicating that an object is nested too deeply to be frozen."""

    def __init__(self, *, max_depth: int | None):
        if max_depth is None:
            message = (
                "The object is nested too deeply to be frozen"
                " within the recursion limit."
            )
        else:
            message = f"The object is nested more than {max_depth} levels deep."
        super().__init__(message)
        self.max_depth = max_depth


class ReferenceCycleError(FreezeError):
    """An exception indicating that an object contains itself."""

    def __init__(self, *, input_type: type):
        super().__init__(
            f"The object contains a reference cycle through an object of type"
            f" {input_type}."
        )
