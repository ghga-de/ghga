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

"""Provides an ObjectIterator for LinkML data."""

from collections.abc import Iterable, Iterator
from copy import deepcopy
from itertools import chain
from numbers import Number
from typing import Optional, Union

from linkml_runtime.linkml_model.meta import ClassDefinitionName, SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView


class RootInferenceError(RuntimeError):
    """This error is produced if the root class could not be determined from a
    LinkML schema.
    """


class ObjectIterator:
    """This iterator class enables iterating through all elements below a
    specified or inferred root element. The iterator returns tuples of an
    elements class name, identifier if present and the corresponding element
    data, which has been re-serialized such that all identifiable inlined
    elements below the element itself have been un-inlined, i.e. replaced by
    their identifiers.
    """

    _schema: SchemaView
    _root: Union[ClassDefinitionName, str]
    _data: dict
    _recursion_iterator: Optional[Iterator]
    _enumerate_non_identifiable: bool
    _inline_non_identifiable: bool
    _path: list

    def __init__(  # noqa: PLR0913
        self,
        schema: SchemaView,
        data: dict,
        root: Optional[str] = None,
        enumerate_non_identifiable=False,
        inline_non_identifiable=True,
        path: Optional[list] = None,
    ):  # pylint: disable=too-many-arguments
        """Creates a new IdentifiedObjectIterator."""
        self._schema = schema
        self._data = data
        self._enumerate_non_identifiable = enumerate_non_identifiable
        self._inline_non_identifiable = inline_non_identifiable
        self._path = path if path else []
        # If a root class was specified, use it
        if root:
            self._root = root
        # ... otherwise, attempt to infer the root class from the provided model.
        else:
            self._root = ObjectIterator._infer_root(schema)

        # Root class slots that we need to recurse into, i.e. all slots with a
        # class range.
        self._recursion_slots = [
            (slot_def.name, slot_def)
            for slot_def in self._schema.class_induced_slots(self._root)
            if slot_def.range in schema.all_classes() and slot_def.inlined is not False
        ]

        self._recursion_iterator = None

    @staticmethod
    def _infer_root(schema: SchemaView) -> ClassDefinitionName:
        """Iterates through all class definitions in a schema and returns the
        name of the single class that is defined as the tree root.

        Raises a RootInferenceError if no or multiple such classes are found.
        """
        # Identify all classes that have tree_root set to true
        root_labeled_classes = [
            name
            for name, definition in schema.all_classes().items()
            if definition.tree_root
        ]

        # If there are no or multiple classes, raise an error
        if not root_labeled_classes:
            raise RootInferenceError("Schema tree root class not found.")
        if len(root_labeled_classes) > 1:
            raise RootInferenceError("Schema has multiple classes defined as tree root")

        return root_labeled_classes[0]

    @staticmethod
    def _re_serialize_element(
        data: dict,
        schema: SchemaView,
        root: Union[str, ClassDefinitionName],
        inline_non_identifiable: bool,
    ):
        """Re-serializes the element serialized in the passed data such that all
        inlined slots are not inlined anymore if the corresponding slot class
        itself has an identifier slot.
        """
        re_serialized_element = {}
        for slot_name, slot_value in data.items():
            slot_def = schema.induced_slot(slot_name, root)
            # If the slot has an inlined class range, transform the inlined
            # value into a reference if it has an identifier slot
            if slot_def.range in schema.all_classes() and slot_def.inlined is not False:
                id_slot: Optional[SlotDefinition] = schema.get_identifier_slot(
                    slot_def.range
                )
                # If the slot class has no identifier, recursively serialize it
                # if enabled
                if id_slot is None and inline_non_identifiable:
                    if slot_def.multivalued:
                        # Sanity check that the slot value is a list
                        if not isinstance(slot_value, list):
                            raise RuntimeError(
                                "Multivalued, inlined slot values must be"
                                " inlined as lists if the slot range itself does"
                                " not have an identifier slot."
                            )
                        re_serialized_element[slot_name] = [
                            ObjectIterator._re_serialize_element(
                                v, schema, slot_def.range, inline_non_identifiable
                            )
                            for v in slot_value
                        ]
                    else:
                        re_serialized_element[
                            slot_name
                        ] = ObjectIterator._re_serialize_element(
                            slot_value,
                            schema,
                            slot_def.range,
                            inline_non_identifiable,
                        )
                elif id_slot is not None:  # noqa: SIM102
                    # If the slot is multivalued, we must differentiate whether it
                    # is inlined as list or as dictionary
                    if slot_def.multivalued:
                        # The data is of type list and this is permitted
                        # according to the slot definition
                        if (
                            slot_def.inlined_as_list or slot_def.inlined_as_list is None
                        ) and isinstance(slot_value, list):
                            re_serialized_element[slot_name] = [
                                elem[id_slot.name] for elem in slot_value
                            ]
                        # The data is of type dict and this is permitted
                        # according to the slot definition
                        elif (
                            slot_def.inlined_as_list is False
                            or slot_def.inlined_as_list is None
                        ) and isinstance(slot_value, dict):
                            re_serialized_element[slot_name] = list(slot_value)
                        # The data is of a type that is not permitted according
                        # to the slot definition
                        else:
                            raise RuntimeError(
                                "Invalid data. Slot is configured as"
                                f" multivalued={slot_def.multivalued} but data is of"
                                f" type {type(slot_value).__name__}"
                            )

            # If the slot is an enum, type or a non-inlined class, keep the
            # value as it is
            else:
                re_serialized_element[slot_name] = slot_value

        return re_serialized_element

    def _re_serialize_root(self):
        """Re-serializes the data stored in this iterator object such that
        inlined slots are not inlined anymore if the corresponding slot class
        itself has an identifier slot.
        """
        return ObjectIterator._re_serialize_element(
            self._data, self._schema, self._root, self._inline_non_identifiable
        )

    def _child_iterators(self) -> Iterable[Iterator]:
        """Returns an iterable of IdentifiedObjectIterator objects for every
        class-range slot of the current root class that has not been iterated
        yet.
        """
        for next_slot_name, next_slot_def in self._recursion_slots:
            if next_slot_name in self._data.keys():  # noqa: SIM118
                # If the slot is not multivalued, a single-value list is returned
                # with an IdentifiedObjectIterator for the value of the slot
                if not next_slot_def.multivalued:
                    yield ObjectIterator(
                        self._schema,
                        self._data[next_slot_name],
                        next_slot_def.range,
                        enumerate_non_identifiable=self._enumerate_non_identifiable,
                        inline_non_identifiable=self._inline_non_identifiable,
                        path=self._path + [next_slot_name],  # noqa: RUF005
                    )
                # If the slot is multivalued and encoded in list format, a list with
                # one IdentifiedObjectIterator per element is returned
                elif (
                    next_slot_def.inlined_as_list
                    or next_slot_def.inlined_as_list is None
                ) and isinstance(self._data[next_slot_name], list):
                    for idx, elem in enumerate(self._data[next_slot_name]):
                        yield ObjectIterator(
                            self._schema,
                            elem,
                            next_slot_def.range,
                            enumerate_non_identifiable=self._enumerate_non_identifiable,
                            inline_non_identifiable=self._inline_non_identifiable,
                            path=self._path + [next_slot_name] + [idx],  # noqa: RUF005
                        )
                # If the slot is multivalued and encoded in dictionary format, a list with
                # one IdentifiedObjectIterator per element is returned. Since the
                # identifier slot is optional in the dictionary format, the
                # identifier is set based on the dictionary keys before the data is
                # used.
                elif (
                    next_slot_def.inlined_as_list is False
                    or next_slot_def.inlined_as_list is None
                ) and isinstance(self._data[next_slot_name], dict):
                    identifier_slot = self._schema.get_identifier_slot(
                        next_slot_def.range
                    )
                    if identifier_slot is None:
                        raise RuntimeError(
                            f"Expected identifier slot for {next_slot_def.range}"
                        )
                    modified_data = deepcopy(self._data[next_slot_name])
                    for key, value in modified_data.items():
                        value[identifier_slot.name] = key
                    for key, elem in modified_data.items():
                        yield ObjectIterator(
                            self._schema,
                            elem,
                            next_slot_def.range,
                            enumerate_non_identifiable=self._enumerate_non_identifiable,
                            inline_non_identifiable=self._inline_non_identifiable,
                            path=self._path + [next_slot_name] + [key],  # noqa: RUF005
                        )
                # If none of the previous conditions were met, we have encountered a
                # data format that is incompatible with the multivalued, inlined and
                # inlined_as_list configurations.
                else:
                    raise RuntimeError(
                        "Invalid data. Slot is configured as"
                        f" inlined_as_list={next_slot_def.inlined_as_list} but data is"
                        f" of type {type(self._data[next_slot_name]).__name__}"
                    )

    def __next__(
        self,
    ) -> tuple[
        Union[str, ClassDefinitionName],
        Optional[Union[str, Number]],
        dict,
        list[Union[str, Number]],
    ]:
        """Select the next element"""
        if self._recursion_iterator is None:
            # Build an iterator for all slots of the root class that have a class range
            self._recursion_iterator = chain.from_iterable(self._child_iterators())

            # De-serialize the root element if it is identifiable
            root_identifier_slot = self._schema.get_identifier_slot(self._root)
            if root_identifier_slot or self._enumerate_non_identifiable:
                return (
                    self._root,  # root element class
                    self._data[root_identifier_slot.name]
                    if root_identifier_slot
                    else None,  # root element identifier
                    self._re_serialize_root(),  # root element data
                    self._path,
                )

        # Pick the next slot with a class range and recurse
        return next(self._recursion_iterator)

    def __iter__(self):
        """Returns the iterator itself."""
        return self
