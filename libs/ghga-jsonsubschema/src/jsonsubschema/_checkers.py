"""JSON Schema type checker class definitions.

Originally created on June 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import copy
import math

import portion
from greenery import parse

import jsonsubschema._constants as definitions
import jsonsubschema._utils as utils
from jsonsubschema import config
from jsonsubschema._utils import print_db
from jsonsubschema.exceptions import (
    UnsupportedNegatedArray,
    UnsupportedNegatedNumeric,
    UnsupportedNegatedObject,
)


class UninhabitedMeta(type):
    """Metaclass that finalizes and validates a schema right after construction.

    After building an instance it updates its internal state, checks whether it
    is uninhabited, and validates it against the JSON Schema validator.
    """

    def __call__(cls, *args, **kwargs):
        """Construct an instance and run its post-initialization checks."""
        obj = type.__call__(cls, *args, **kwargs)
        obj.update_internal_state()
        obj.is_uninhabited()
        utils.validate_schema(obj)
        return obj


class JSONschema(dict, metaclass=UninhabitedMeta):
    """Base class for canonicalized schemas with meet, join and subtype operations.

    A ``JSONschema`` is a ``dict`` holding the schema keywords together with the
    type-specific logic to compute the meet (intersection), join (union) and
    subtype (``<:``) relation against another schema. Subclasses implement the
    per-type behavior via the ``_meet``, ``_join`` and ``_is_subtype`` hooks.
    """

    type: str  # the JSON type ("integer", ...) or connector kind ("anyOf", ...)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Since one might call this constructor directly with a JSONschema
        # as the parameter, also validate that the actual parameter, after
        # being built into a normal dict, is a valid schema.
        utils.validate_schema(self)

        # Instead of adding enum at every child constructor,
        # do it here once and for all.
        if "enum" in self:
            self.enum = self["enum"]

    def update_internal_state(self):
        """Derive cached attributes (e.g. intervals) from the schema keywords."""

    def _is_uninhabited(self) -> bool:
        """Return whether this schema type is uninhabited (matches no value)."""
        return False

    def _meet(self, s: "JSONschema") -> "JSONschema":
        """Compute the meet (intersection) with schema ``s``; overridden per type."""
        raise NotImplementedError

    def _is_subtype(self, s: "JSONschema") -> bool:
        """Return whether ``self`` is a subtype of ``s``; overridden per type."""
        raise NotImplementedError

    def _is_subtype_non_trivial(self, s: "JSONschema") -> bool:
        """Handle subtype checks that require reasoning across an ``anyOf`` union."""
        raise NotImplementedError

    @staticmethod
    def neg(s):
        """Return a schema describing the negation (complement) of ``s``."""
        raise NotImplementedError

    def is_boolean(self):
        """Return whether this schema is built from boolean connectors."""
        return self.keys() & definitions.Jconnectors

    def has_enum(self):
        """Return whether this schema constrains values via an ``enum``."""
        return "enum" in self.keys() or hasattr(self, "enum")

    def is_uninhabited(self):
        """Return whether this schema is uninhabited, warning if so when enabled."""
        # Don't store an uninhabited flag, but rather re-check on the fly
        # to get an updated result based on the current internal state.
        uninhabited = self._is_uninhabited()
        if config.WARN_UNINHABITED and uninhabited:
            print("Found an uninhabited type at: ", type(self), self)
        return uninhabited

    def meet(self, s):
        """Return the meet (intersection) of this schema with ``s``.

        Handles the trivial top/bottom cases and delegates the rest to ``_meet``.
        """
        if is_top(s):
            return self
        if is_top(self):
            return s
        if is_bot(self) or is_bot(s):
            return JSONbot()
        return self._meet(s)

    def meet_handle_rhs(self, s, meet_cb):
        """Dispatch the meet: distribute over ``s`` if it is an ``anyOf`` union.

        Otherwise apply the type-specific ``meet_cb`` callback.
        """
        if s.type == "anyOf":
            return JSONanyOf._meet_any_of(s, self)

        return meet_cb(self, s)

    def _join(self, s):
        """Place holder in case a subclass does not implement its own join.
        Should be removed once we are done fully implementing join
        """
        ret = {"anyOf": [self, s]}
        return JSONanyOf(ret)

    def join(self, s):
        """Return the join (union) of this schema with ``s``.

        Handles the trivial top/bottom cases, merges enums where possible, and
        delegates the rest to ``_join``.
        """
        if is_bot(s):
            return self
        if is_bot(self):
            return s
        if is_top(self) or is_top(s):
            return JSONtop()
        ret = self._join(s)
        if self.has_enum() and s.has_enum():
            enum = JSONschema.join_enum(self, s)
            if enum:
                ret.enum = ret["enum"] = list(enum)
        # instead of returning uninhabited types, return bot
        if is_bot(ret):
            return JSONbot()
        return ret

    @staticmethod
    def join_enum(s1, s2):
        """Return the union of the enum values of two same-typed schemas."""
        if s1.type == s2.type:
            try:
                return sorted(set(s1.enum) | set(s2.enum))
            except TypeError:
                # enum values may be unhashable (list/dict) or unorderable
                return s1.enum + s2.enum
        return None

    def is_subtype(self, s):
        """Return whether this schema is a subtype (``<:``) of ``s``.

        Handles the trivial top/bottom cases and the enum check, then delegates
        the rest to ``_is_subtype``.
        """
        if is_bot(self) or is_top(s):
            return True
        if (not is_bot(self) and is_bot(s)) or (is_top(self) and not is_top(s)):
            return False
        return self.subtype_enum(s) and self._is_subtype(s)

    def is_subtype_non_trivial(self, s):
        """Run the non-trivial subtype check against an ``anyOf`` union ``s``."""
        return self._is_subtype_non_trivial(s)

    def subtype_enum(self, s):
        """Return whether every enum value of this schema is also valid under ``s``."""
        if self.has_enum():
            valid_enum = utils.get_valid_enum_vals(self.enum, s)
            # no need to check individual elements
            # as enum values are unique by definition
            return len(valid_enum) == len(self.enum)
        return True

    def is_subtype_handle_rhs(self, s, is_subtype_cb):
        """Dispatch the subtype check, handling an ``anyOf`` union on the right side.

        Otherwise apply the type-specific ``is_subtype_cb`` callback.
        """
        if s.is_boolean() and s.type == "anyOf":
            if not s.nonTrivialJoin:
                return any(is_subtype_cb(self, i) for i in s.anyOf)
            return self.is_subtype_non_trivial(s)

        return is_subtype_cb(self, s)


class JSONtop(JSONschema):
    """The top schema ``{}`` that every value satisfies."""

    def __init__(self):
        super().__init__({})
        self.type = "top"

    def _is_uninhabited(self):
        """Return ``False``: top is always inhabited."""
        return False

    def _meet(self, s):
        """Return ``s``: meeting with top yields the other schema."""
        return s

    def _join(self, s):
        """Return top: joining with top yields top."""
        return self

    def _is_subtype(self, s):
        """Return whether ``s`` is also top (the only supertype of top)."""

        def _is_top_subtype(s1, s2):
            return bool(is_top(s2))

        super().is_subtype_handle_rhs(s, _is_top_subtype)

    def __eq__(self, s):
        return bool(is_top(s))

    def __repr__(self):
        return "JSON_TOP"

    def __bool__(self):
        return True


def is_top(obj):
    """Return whether ``obj`` is the top schema (``True``, ``{}`` or JSONtop)."""
    return obj is True or obj == {} or isinstance(obj, JSONtop)


class JSONbot(JSONschema):
    """The bottom schema ``{"not": {}}`` that no value satisfies."""

    def __init__(self):
        super().__init__({"not": {}})
        self.type = "bot"

    def _is_uninhabited(self):
        """Return ``True``: bottom is uninhabited by definition."""
        return True

    def _meet(self, s):
        """Return bottom: meeting with bottom yields bottom."""
        return self

    def _join(self, s):
        """Return ``s``: joining with bottom yields the other schema."""
        return s

    def _is_subtype(self, s):
        """Return whether ``s`` is also bottom (bottom is a subtype of everything)."""

        def _is_bot_subtype(s1, s2):
            return bool(is_bot(s2))

        super().is_subtype_handle_rhs(s, _is_bot_subtype)

    def __eq__(self, s):
        return bool(is_bot(s))

    def __repr__(self):
        return "JSON_BOT"

    def __bool__(self):
        return False


def is_bot(obj):
    """Return whether ``obj`` represents the bottom schema (uninhabited)."""
    return (
        obj is False
        or (utils.is_dict(obj) and obj.get("not") == {})
        or isinstance(obj, JSONbot)
        or (isinstance(obj, JSONschema) and obj.is_uninhabited())
    )


class JSONTypeString(JSONschema):
    """Schema for the JSON ``string`` type (length bounds and ``pattern``)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "string"
        self.minLength = self.get("minLength", 0)
        self.maxLength = self.get("maxLength", portion.inf)
        # json regexes are not anchored but the greenery library we use
        # for regex inclusion assumes anchored regexes. So
        # pad the regex with '.*' from both sides.
        if "pattern" in s:
            patrn = utils.regex_unanchor(s["pattern"])
            self.pattern = utils.prepare_pattern_for_greenry(patrn)
        else:
            self.pattern = ""

    def _is_uninhabited(self):
        """Return whether the length bounds are contradictory (min > max).

        Detecting a contradiction between the pattern and the length bounds
        would require an expensive regex intersection, so that check is
        deferred to the actual subtype check.
        """
        return self.minLength > self.maxLength

    def update_internal_state(self):
        """Cache the length interval derived from ``minLength`` and ``maxLength``."""
        self.interval = portion.closed(self.minLength, self.maxLength)

    def _meet(self, s):
        """Meet with ``s``, intersecting length bounds and patterns for strings."""

        def _meet_string(s1, s2):
            if s2.type == "string":
                ret = {}
                mn = max(s1.minLength, s2.minLength)
                if utils.is_num(mn):
                    ret["minLength"] = mn
                mx = min(s1.maxLength, s2.maxLength)
                if utils.is_num(mx):
                    ret["maxLength"] = mx
                # Explicitly anchor pattern when assigned to the json key
                # to reflect the greenery lib behavior on the json object.
                patrn = utils.regex_meet(s1.pattern, s2.pattern)
                if patrn:
                    ret["pattern"] = "^" + patrn + "$"
                return JSONTypeString(ret)
            return JSONbot()

        return super().meet_handle_rhs(s, _meet_string)

    def _join(self, s):
        """Join with ``s``, merging length bounds and patterns when both are strings."""

        def _join_string(s1, s2):
            if s2.type == "string":
                ret = {}
                mn = min(s1.minLength, s2.minLength)
                if utils.is_num(mn):
                    ret["minLength"] = mn
                mx = max(s1.maxLength, s2.maxLength)
                if utils.is_num(mx):
                    ret["maxLength"] = mx
                if s1.minLength == 0 and s1.maxLength == portion.inf:
                    s1_range = None
                else:
                    s1_range = utils.string_range_to_regex(s1.minLength, s1.maxLength)
                if s2.minLength == 0 and s2.maxLength == portion.inf:
                    s2_range = None
                else:
                    s2_range = utils.string_range_to_regex(s2.minLength, s2.maxLength)
                s1_new_pattern = utils.regex_meet(s1_range, s1.pattern)
                s2_new_pattern = utils.regex_meet(s2_range, s2.pattern)
                if s1_new_pattern and s2_new_pattern:
                    ret["pattern"] = "^" + s1_new_pattern + "$|^" + s2_new_pattern + "$"
                return JSONTypeString(ret)
            return JSONanyOf({"anyOf": [s1, s2]})

        return _join_string(self, s)

    def _is_subtype(self, s):
        """Return whether this string schema is a subtype of ``s``."""

        def _is_string_subtype(s1, s2):
            if s2.type == "string":
                is_sub_interval = s1.interval in s2.interval
                if not is_sub_interval and not s1.pattern and not s2.pattern:
                    return False
                if s1.pattern == s2.pattern:
                    return True
                if s1.has_enum():
                    return super().subtype_enum(s2)
                if s1.minLength == 0 and s1.maxLength == portion.inf:
                    pattern1 = s1.pattern
                else:
                    s1_range = utils.string_range_to_regex(s1.minLength, s1.maxLength)
                    pattern1 = utils.regex_meet(s1_range, s1.pattern)

                if s2.minLength == 0 and s2.maxLength == portion.inf:
                    pattern2 = s2.pattern
                else:
                    s2_range = utils.string_range_to_regex(s2.minLength, s2.maxLength)
                    pattern2 = utils.regex_meet(s2_range, s2.pattern)

                return bool(utils.regex_is_subset(pattern1, pattern2))
            return False

        return super().is_subtype_handle_rhs(s, _is_string_subtype)

    @staticmethod
    def neg(s):
        """Return the complement of the string schema ``s`` (non-strings plus gaps)."""
        negated_strings = []
        non_string = bool_to_constructor["anyOf"](
            {"anyOf": get_default_types_except("string")}
        )

        if "minLength" in s and s["minLength"] - 1 >= 0:
            negated_strings.append(JSONTypeString({"maxLength": s["minLength"] - 1}))
        if "maxLength" in s:
            negated_strings.append(JSONTypeString({"minLength": s["maxLength"] + 1}))
        if "pattern" in s:
            # Explicitly anchor pattern when assigned to the json key
            # to reflect the greenery lib behavior on the json object.
            patrn = utils.prepare_pattern_for_greenry(
                utils.regex_unanchor(s["pattern"])
            )
            negated_strings.append(
                JSONTypeString(
                    {"pattern": "^" + utils.complement_of_string_pattern(patrn) + "$"}
                )
            )

        if len(negated_strings) == 0:
            return non_string
        joined_string = bool_to_constructor["anyOf"]({"anyOf": negated_strings})
        return non_string.join(joined_string)


class JSONTypeNumeric(JSONschema):
    """Common base for the numeric JSON types ``integer`` and ``number``.

    Holds the shared range and ``multipleOf`` handling; subclasses build the
    concrete interval and define their own join/subtype behavior.
    """

    def __init__(self, s):
        super().__init__(s)
        self.minimum = self.get("minimum", -portion.inf)
        self.maximum = self.get("maximum", portion.inf)
        self.exclusiveMinimum = self.get("exclusiveMinimum", False)
        self.exclusiveMaximum = self.get("exclusiveMaximum", False)
        self.multipleOf = self.get("multipleOf", None)
        # "number but not an integer": negating an integer schema embeds the
        # standard fragment {"not": {"multipleOf": 1}} into the number schema
        self.notInteger = self.get("not") == {"multipleOf": 1}
        self.interval = (
            portion.empty()
        )  # set by build_interval_draft4() via update_internal_state

    def build_interval_draft4(self):
        """Build the cached numeric interval; implemented by each subclass."""
        raise NotImplementedError

    def _is_uninhabited(self):
        """Return whether the interval is empty or the constraints conflict."""
        if self.notInteger and (
            self.type == "integer"
            or utils.is_int_equiv(self.multipleOf)
            or (
                not self.interval.empty
                and self.interval.lower == self.interval.upper
                and utils.is_int_equiv(self.interval.lower)
            )
        ):
            # every admitted value would have to be an integer
            return True
        if self.interval.empty:
            return True
        if utils.is_num(self.multipleOf):
            # for integers, the admitted values are the integer-valued
            # multiples of the factor
            step = (
                utils.integer_valued_multiple_step(self.multipleOf)
                if self.type == "integer"
                else self.multipleOf
            )
            return not utils.interval_contains_multiple_of(self.interval, step)
        return False

    def update_internal_state(self):
        """Cache the numeric interval via ``build_interval_draft4``."""
        if (
            self.notInteger
            and utils.is_num(self.multipleOf)
            and not utils.is_int_equiv(self.multipleOf)
        ):
            # the meet/subtype rules for not-integer schemas assume there is
            # no fractional multipleOf; fail loudly instead of approximating
            raise UnsupportedNegatedNumeric(schema=self)
        self.build_interval_draft4()

    def single_value(self):
        """Return the only value in the interval, or ``None`` if not degenerate."""
        if not self.interval.empty and self.interval.lower == self.interval.upper:
            return self.interval.lower
        return None

    @staticmethod
    def _subtype_by_values(s1, s2):
        """Return an exact subtype verdict for value-enumerable schemas.

        Schemas restricted by an ``enum`` or admitting only a single value
        are decided by validating their values against ``s2``. Returns
        ``None`` when ``s1`` is not value-enumerable.
        """
        if s1.has_enum():
            return s1.subtype_enum(s2)
        value = s1.single_value()
        if value is not None:
            return bool(utils.get_valid_enum_vals([value], s2))
        return None

    @staticmethod
    def _multipleof_compatible(lhs_multiple_of, rhs_multiple_of):
        """Return whether ``lhs`` values are always multiples of the ``rhs`` factor."""
        return (
            lhs_multiple_of == rhs_multiple_of
            or (lhs_multiple_of is not None and rhs_multiple_of is None)
            or (
                lhs_multiple_of is not None
                and rhs_multiple_of is not None
                and lhs_multiple_of % rhs_multiple_of == 0
            )
        )

    @staticmethod
    def _multipleof_compatible_integer_lhs(lhs_multiple_of, rhs_multiple_of):
        """Like ``_multipleof_compatible`` but for an integer left-hand side.

        Every integer is a multiple of ``1/q`` (e.g. of ``0.5``), which is
        the case exactly when the integer-valued multiples of the right-hand
        factor have a spacing of 1.
        """
        return JSONTypeNumeric._multipleof_compatible(
            lhs_multiple_of, rhs_multiple_of
        ) or (
            lhs_multiple_of is None
            and rhs_multiple_of is not None
            and utils.integer_valued_multiple_step(rhs_multiple_of) == 1
        )

    @staticmethod
    def _multipleof_compatible_integer_rhs(lhs_multiple_of, rhs_multiple_of):
        """Like ``_multipleof_compatible`` but for an integer right-hand side."""
        return rhs_multiple_of is None or (
            lhs_multiple_of is not None
            and rhs_multiple_of is not None
            and lhs_multiple_of % rhs_multiple_of == 0
        )

    @staticmethod
    def _interval_to_bounds(interval):
        """Return the minimum/maximum keywords describing ``interval``."""
        ret: dict = {}
        if utils.is_num(interval.lower):
            ret["minimum"] = interval.lower
            if interval.left == portion.OPEN:
                ret["exclusiveMinimum"] = True
        if utils.is_num(interval.upper):
            ret["maximum"] = interval.upper
            if interval.right == portion.OPEN:
                ret["exclusiveMaximum"] = True
        return ret

    def _meet(self, s):
        """Meet with ``s``, intersecting ranges and combining ``multipleOf`` factors."""

        def _meet_numeric(s1, s2):
            if (
                s1.type not in definitions.Jnumeric
                or s2.type not in definitions.Jnumeric
            ):
                return JSONbot()
            not_integer = s1.notInteger or s2.notInteger
            if not_integer and (s1.type == "integer" or s2.type == "integer"):
                # no integer is a non-integer number
                return JSONbot()

            # intersect the cached intervals so that exclusive
            # minimum/maximum bounds are honored
            interval = s1.interval & s2.interval
            if interval.empty:
                return JSONbot()

            ret = JSONTypeNumeric._interval_to_bounds(interval)
            if not_integer:
                ret["not"] = {"multipleOf": 1}
            mul_of = utils.lcm(s1.multipleOf, s2.multipleOf)
            if mul_of:
                ret["multipleOf"] = mul_of

            if s1.type == s2.type == "number":
                return JSONTypeNumber(ret)
            # case one of them or both are integers
            return JSONTypeInteger(ret)

        return super().meet_handle_rhs(s, _meet_numeric)

    def _join(self, s):
        """Join with ``s`` as an ``anyOf`` (e.g. joining an integer with a number)."""
        # join integer with number
        return JSONanyOf({"anyOf": [self, s]})

    def is_subtype_handle_rhs(self, s, is_subtype_cb):
        """Dispatch the numeric subtype check, handling union right-hand sides.

        A union produced by negating a schema records the negated schema, so
        the check reduces to an emptiness test of the meet with it. Other
        unions involving not-integer schemas need an exact coverage check of
        this schema against the union members, since no single member needs
        to contain it as a whole.
        """
        if s.is_boolean() and s.type == "anyOf":
            if self.has_enum():
                # validating the enum values against the whole union is exact
                # even when they are spread over several union members
                return self.subtype_enum(s)
            if getattr(s, "complementOf", None) is not None:
                # self <: not(X) holds iff meet(self, X) is uninhabited
                return is_bot(self.meet(s.complementOf))
            if self.notInteger or any(getattr(i, "notInteger", False) for i in s.anyOf):
                if any(is_subtype_cb(self, i) for i in s.anyOf):
                    return True
                return self._is_covered_by_numeric_union(s)
        return super().is_subtype_handle_rhs(s, is_subtype_cb)

    def _is_covered_by_numeric_union(self, s):
        """Return whether the union ``s`` covers every value of this schema.

        This is exact for schemas without ``multipleOf``: the non-integer
        values must be covered by the plain number and not-integer members
        and the integer values by the plain number and integer members.
        Unions mixing not-integer schemas with ``multipleOf`` constraints
        cannot be decided and raise ``UnsupportedNegatedNumeric``.
        """
        members = [i for i in s.anyOf if i.type in definitions.Jnumeric]
        if utils.is_num(self.multipleOf) or any(
            utils.is_num(i.multipleOf) for i in members
        ):
            raise UnsupportedNegatedNumeric(schema=self)

        plain_numbers = portion.empty()
        non_integers = portion.empty()
        integers = portion.empty()
        for member in members:
            if member.type == "integer":
                integers |= member.interval
            elif member.notInteger:
                non_integers |= member.interval
            else:
                plain_numbers |= member.interval

        if self.type == "integer":
            return not utils.interval_contains_integer(
                self.interval - plain_numbers - integers
            )
        if not utils.interval_diff_is_integer_points(
            self.interval, plain_numbers | non_integers
        ):
            # some non-integer value is not covered
            return False
        if self.notInteger:
            return True
        return not utils.interval_contains_integer(
            self.interval - plain_numbers - integers
        )


class JSONTypeInteger(JSONTypeNumeric):
    """Schema for the JSON ``integer`` type."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "integer"

    def build_interval_draft4(self):
        """Build the integer interval, rounding bounds and applying ``multipleOf``."""
        # min, max, and interval attributes handle
        # exclusive min/max as well as float values
        # of min/max.
        # All type operations such as meet, join,
        # and subtype should rely only on interval
        # and min/max attributes.

        if self.exclusiveMinimum:
            if utils.is_int_equiv(self.minimum):
                self.minimum = self.minimum + 1
            else:
                self.minimum = math.ceil(self.minimum)
        elif utils.is_num(self.minimum):
            self.minimum = math.ceil(self.minimum)

        if self.exclusiveMaximum:
            if utils.is_int_equiv(self.maximum):
                self.maximum = self.maximum - 1
            else:
                self.maximum = math.floor(self.maximum)
        elif utils.is_num(self.maximum):
            self.maximum = math.floor(self.maximum)

        self.minimum, self.maximum = utils.get_new_min_max_with_mulof(
            self.minimum, self.maximum, self.multipleOf
        )

        self.interval = portion.closed(self.minimum, self.maximum)

    def _join(self, s):
        """Join with ``s``, merging mergeable integer intervals where possible."""

        def _join_integer(s1, s2):
            print_db("Trying to joinInteger")
            if s2.type == "integer":
                ret = {}
                if utils.are_intervals_mergable(s1.interval, s2.interval):
                    if not s1.multipleOf and not s2.multipleOf:
                        joined_interval = s1.interval | s2.interval
                        if utils.is_num(joined_interval.lower):
                            ret["minimum"] = joined_interval.lower
                        if utils.is_num(joined_interval.upper):
                            ret["maximum"] = joined_interval.upper
                        return JSONTypeInteger(ret)
                    if (s1.multipleOf and utils.is_interval_finite(s1.interval)) or (
                        s2.multipleOf and utils.is_interval_finite(s2.interval)
                    ):
                        ret = JSONanyOf({"anyOf": [s1, s2]})
                        ret.nonTrivialJoin = True
                        return ret

            print_db("NonTrivial is not set")
            return JSONanyOf({"anyOf": [s1, s2]})

        return _join_integer(self, s)

    def _is_subtype(self, s):
        """Return whether this integer schema is a subtype of ``s``."""

        def _is_integer_subtype(s1, s2):
            if s2.type not in definitions.Jnumeric:
                return False
            verdict = JSONTypeNumeric._subtype_by_values(s1, s2)
            if verdict is not None:
                return verdict
            if s2.notInteger:
                print_db("num__05")
                return False
            if s1.interval not in s2.interval:
                print_db("num__00")
                return False
            if JSONTypeNumeric._multipleof_compatible_integer_lhs(
                s1.multipleOf, s2.multipleOf
            ):
                print_db("num__01")
                return True
            return None

        return super().is_subtype_handle_rhs(s, _is_integer_subtype)

    def _is_subtype_non_trivial(self, s):  # noqa: C901, PLR0912
        """Check subtyping against an ``anyOf`` of numeric schemas by enumeration.

        Merges the union's intervals and verifies that every integer allowed by
        this schema is covered by at least one member of the union.
        """
        print_db("Nontrivial Integer subtype")
        if s.type == "anyOf":
            intervals: list = []
            interval_to_mulofs = {}
            for num_schema in s.anyOf:
                if num_schema.interval not in interval_to_mulofs:
                    interval_to_mulofs[num_schema.interval] = (
                        [num_schema.multipleOf] if num_schema.multipleOf else []
                    )
                elif num_schema.multipleOf:
                    interval_to_mulofs[num_schema.interval].append(
                        num_schema.multipleOf
                    )

                added = False
                for j in list(intervals):
                    if utils.are_intervals_mergable(num_schema.interval, j):
                        intervals.remove(j)
                        intervals.append((num_schema.interval | j).enclosure)
                        added = True
                if not added:
                    intervals.append(num_schema.interval)

            mulof = [self.multipleOf] if self.multipleOf else []
            for x in utils.generate_range_with_multipleof(
                range(self.minimum, self.maximum + 1), mulof, []
            ):
                for interv, m in interval_to_mulofs.items():
                    if x in interv:
                        if m:
                            if any(x % i == 0 for i in m if i is not None):
                                break
                        else:
                            break
                else:
                    return False

            return True
        return None

    @staticmethod
    def _integer_bounds(s):
        """Return the inclusive integer bounds ``(lo, hi)`` of the schema ``s``.

        Either bound is ``None`` when the schema does not constrain it.
        """
        lo = hi = None
        if "minimum" in s:
            if s.get("exclusiveMinimum"):
                lo = math.floor(s["minimum"]) + 1
            else:
                lo = math.ceil(s["minimum"])
        if "maximum" in s:
            if s.get("exclusiveMaximum"):
                hi = math.ceil(s["maximum"]) - 1
            else:
                hi = math.floor(s["maximum"])
        return lo, hi

    @staticmethod
    def neg(s):
        """Return the exact complement of the integer schema ``s``.

        The complement consists of all non-numeric values, the numbers that
        are not integers (embedded as ``{"not": {"multipleOf": 1}}``), and
        the integers outside the schema's bounds. Negating an integer
        ``multipleOf`` schema would additionally need "integer but not a
        multiple of k", which the checker language cannot express, so that
        case raises ``UnsupportedNegatedNumeric`` instead of yielding
        unsound subtype verdicts. A trivial ``multipleOf`` of 1 does not
        constrain integers and is simply ignored.
        """
        if s.get("multipleOf") == 1:
            s = {k: v for k, v in s.items() if k != "multipleOf"}
        elif "multipleOf" in s:
            raise UnsupportedNegatedNumeric(schema=s)

        lo, hi = JSONTypeInteger._integer_bounds(s)
        if lo is not None and hi is not None and lo > hi:
            return JSONtop()  # uninhabited, so the complement is everything

        parts = [
            *get_default_types_except("number", "integer"),
            JSONTypeNumber({"not": {"multipleOf": 1}}),
        ]
        if lo is not None:
            parts.append(JSONTypeInteger({"maximum": lo - 1}))
        if hi is not None:
            parts.append(JSONTypeInteger({"minimum": hi + 1}))
        result = bool_to_constructor["anyOf"]({"anyOf": parts})
        if isinstance(result, JSONanyOf):
            # remember the negated schema: lhs <: not(X) iff meet(lhs, X)
            # is uninhabited, which numeric meets can decide exactly
            result.complementOf = JSONTypeInteger(s)
        return result


class JSONTypeNumber(JSONTypeNumeric):
    """Schema for the JSON ``number`` type (integers and reals)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "number"

    def build_interval_draft4(self):
        """Build the number interval, honoring exclusive minimum/maximum bounds."""
        if self.exclusiveMinimum and self.exclusiveMaximum:
            self.interval = portion.open(self.minimum, self.maximum)
        elif self.exclusiveMinimum:
            self.interval = portion.openclosed(self.minimum, self.maximum)
        elif self.exclusiveMaximum:
            self.interval = portion.closedopen(self.minimum, self.maximum)
        else:
            self.interval = portion.closed(self.minimum, self.maximum)

    def _join(self, s):
        """Join with ``s``, merging overlapping numeric intervals where possible."""

        def _join_number(s1, s2):
            if s2.type in definitions.Jnumeric:
                if s1.notInteger != s2.notInteger:
                    # a not-integer schema cannot merge intervals with one
                    # that admits integers, so keep the union as is
                    return JSONanyOf({"anyOf": [s1, s2]})
                if not s1.interval.overlaps(s2.interval):
                    return JSONanyOf({"anyOf": [s1, s2]})
                ret = JSONTypeNumeric._interval_to_bounds(s1.interval | s2.interval)
                if s1.notInteger:
                    ret["not"] = {"multipleOf": 1}
                gcd = utils.gcd(s1.multipleOf, s2.multipleOf)
                if utils.is_num(gcd) and gcd != 1:
                    ret["multipleOf"] = gcd

                if s2.type == "integer":
                    return JSONanyOf({"anyOf": [s1, JSONTypeInteger(ret)]})
                return JSONTypeNumber(ret)
            return JSONanyOf({"anyOf": [s1, s2]})

        return _join_number(self, s)

    def _is_subtype(self, s):
        """Return whether this number schema is a subtype of ``s``."""

        def _is_number_subtype(s1, s2):
            match s2.type:
                case "number":
                    return JSONTypeNumber._is_subtype_of_number(s1, s2)
                case "integer":
                    return JSONTypeNumber._is_subtype_of_integer(s1, s2)
                case _:
                    print_db("num__04")
                    return False

        return super().is_subtype_handle_rhs(s, _is_number_subtype)

    @staticmethod
    def _is_subtype_of_number(s1, s2):
        """Return whether number schema ``s1`` is a subtype of number ``s2``."""
        verdict = JSONTypeNumeric._subtype_by_values(s1, s2)
        if verdict is not None:
            return verdict
        if s2.notInteger:
            return JSONTypeNumber._is_subtype_of_non_integer(s1, s2)
        if s1.notInteger:
            if utils.is_num(s2.multipleOf):
                # a dense set of non-integers cannot fit into a
                # discrete set of multiples
                print_db("num__06")
                verdict = False
            else:
                verdict = utils.interval_diff_is_integer_points(
                    s1.interval, s2.interval
                )
            return verdict
        if s1.interval not in s2.interval:
            print_db("num__00")
            return False
        if JSONTypeNumeric._multipleof_compatible(s1.multipleOf, s2.multipleOf):
            print_db("num__01")
            return True
        return None

    @staticmethod
    def _is_subtype_of_integer(s1, s2):
        """Return whether number schema ``s1`` is a subtype of integer ``s2``."""
        verdict = JSONTypeNumeric._subtype_by_values(s1, s2)
        if verdict is not None:
            return verdict
        if s1.notInteger:
            print_db("num__07")
            return False
        if s1.interval not in s2.interval:
            print_db("num__02")
            return False
        if utils.is_int_equiv(s1.multipleOf) and (
            JSONTypeNumeric._multipleof_compatible_integer_rhs(
                s1.multipleOf, s2.multipleOf
            )
        ):
            print_db("num__03")
            return True
        return None

    @staticmethod
    def _is_subtype_of_non_integer(s1, s2):
        """Return whether ``s1`` fits the not-integer number schema ``s2``.

        Every value of ``s1`` must lie in the interval of ``s2`` and must not
        be an integer. Single-value schemas are already handled by the caller.
        """
        if s1.multipleOf is None:
            if s1.notInteger:
                # values missing from the rhs interval must all be integers
                return utils.interval_diff_is_integer_points(s1.interval, s2.interval)
            if utils.interval_contains_integer(s1.interval):
                return False
            return s1.interval in s2.interval
        step = utils.integer_valued_multiple_step(s1.multipleOf)
        if utils.interval_contains_multiple_of(s1.interval, step):
            # some multiple of s1.multipleOf in the interval is an integer
            return False
        return not utils.interval_contains_multiple_of(
            s1.interval - s2.interval, s1.multipleOf
        )

    @staticmethod
    def neg(s):
        """Return the complement of the number schema ``s`` (non-numbers plus gaps).

        A number schema with ``multipleOf`` 1 admits exactly the integers in
        its bounds, so its complement is that of the corresponding integer
        schema. Raise ``UnsupportedNegatedNumeric`` for other ``multipleOf``
        factors: their complement contains the non-multiples, which the
        checker language cannot express, and a smaller complement would
        yield unsound verdicts.
        """
        if s.get("multipleOf") == 1:
            return JSONTypeInteger.neg(
                {k: v for k, v in s.items() if k != "multipleOf"}
            )
        if "multipleOf" in s:
            raise UnsupportedNegatedNumeric(schema=s)

        negated_numbers = []
        non_numbers = bool_to_constructor["anyOf"](
            {"anyOf": get_default_types_except("number", "integer")}
        )

        if "minimum" in s:
            if s.get("exclusiveMinimum"):
                negated_numbers.append(JSONTypeNumber({"maximum": s["minimum"]}))
            else:
                negated_numbers.append(
                    JSONTypeNumber({"maximum": s["minimum"], "exclusiveMaximum": True})
                )
        if "maximum" in s:
            if s.get("exclusiveMaximum"):
                negated_numbers.append(JSONTypeNumber({"minimum": s["maximum"]}))
            else:
                negated_numbers.append(
                    JSONTypeNumber({"minimum": s["maximum"], "exclusiveMinimum": True})
                )

        if negated_numbers:
            joined_numbers = bool_to_constructor["anyOf"]({"anyOf": negated_numbers})
            result = non_numbers.join(joined_numbers)
        else:
            result = non_numbers
        if isinstance(result, JSONanyOf):
            # remember the negated schema: lhs <: not(X) iff meet(lhs, X)
            # is uninhabited, which numeric meets can decide exactly
            result.complementOf = JSONTypeNumber(s)
        return result


class JSONTypeBoolean(JSONschema):
    """Schema for the JSON ``boolean`` type (optionally restricted by ``enum``)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "boolean"

    def _is_uninhabited(self):
        """Return ``False``: a boolean schema is always inhabited."""
        return False

    def _meet(self, s):
        """Meet with ``s``, intersecting the allowed boolean values."""

        def _meet_boolean(s1, s2):
            if s2.type == "boolean":
                if s1.has_enum() and s2.has_enum():
                    _overlap = set(s1.enum).intersection(s2.enum)
                    if _overlap:
                        return JSONTypeBoolean({"enum": list(_overlap)})
                    return JSONbot()
                if s1.has_enum():
                    return JSONTypeBoolean({"enum": s1.enum})
                if s2.has_enum():
                    return JSONTypeBoolean({"enum": s2.enum})
                return JSONTypeBoolean({})
            return JSONbot()

        return super().meet_handle_rhs(s, _meet_boolean)

    def _is_subtype(self, s):
        """Return whether this boolean schema is a subtype of ``s``."""

        def _is_boolean_subtype(self, s2):
            return s2.type == "boolean"

        return super().is_subtype_handle_rhs(s, _is_boolean_subtype)

    @staticmethod
    def neg(s):
        """Return the complement of the boolean schema ``s``."""
        non_boolean = bool_to_constructor["anyOf"](
            {"anyOf": get_default_types_except("boolean")}
        )

        # booleans are allowed to keep enums, so check if any
        _enum = s.get("enum")
        if _enum and len(_enum) == 1:  # exactly negating one value, return the other
            return non_boolean.join(JSONTypeBoolean({"enum": [not _enum[0]]}))

        return non_boolean


class JSONTypeNull(JSONschema):
    """Schema for the JSON ``null`` type (the single value ``null``)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "null"

    def _is_uninhabited(self):
        """Return ``False``: the null schema is always inhabited."""
        return False

    def _meet(self, s):
        """Meet with ``s``: null if ``s`` is also null, otherwise bottom."""

        def _meet_null(s1, s2):

            if s2.type == "null":
                return s1
            return JSONbot()

        return super().meet_handle_rhs(s, _meet_null)

    def _is_subtype(self, s):
        """Return whether ``s`` is also a null schema."""

        def _is_null_subtype(self, s2):
            return s2.type == "null"

        return super().is_subtype_handle_rhs(s, _is_null_subtype)

    @staticmethod
    def neg(s):
        """Return the complement of the null schema (all non-null types)."""
        return bool_to_constructor["anyOf"]({"anyOf": get_default_types_except("null")})


class JSONTypeArray(JSONschema):
    """Schema for the JSON ``array`` type (item schemas, length and uniqueness)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "array"
        self.minItems = self.get("minItems", 0)
        self.maxItems = self.get("maxItems", portion.inf)
        self.items_ = self.get("items", JSONtop())
        self.additionalItems = self.get("additionalItems", True)
        self.uniqueItems = self.get("uniqueItems", False)

    def compute_actual_max_items(self):
        """Tighten ``maxItems`` when a fixed item tuple forbids additional items."""
        if utils.is_list(self.items_) and is_bot(self.additionalItems):
            new_max = min(self.maxItems, len(self.items_))
            if new_max != self.maxItems:
                self.maxItems = new_max

    def _is_uninhabited(self):
        """Return whether the length bounds or item constraints admit no array."""
        return (
            (self.minItems > self.maxItems)
            or (
                utils.is_list(self.items_)
                and is_bot(self.additionalItems)
                and self.minItems > len(self.items_)
            )
            or (utils.is_list(self.items_) and len(self.items_) == 0)
        )

    def update_internal_state(self):
        """Cache the length interval and normalize ``additionalItems``."""
        self.compute_actual_max_items()
        self.interval = portion.closed(self.minItems, self.maxItems)
        if utils.is_list(self.items_) and len(self.items_) == self.maxItems:
            self.additionalItems = False

    def _meet(self, s):
        """Meet with ``s``, intersecting length, uniqueness and item schemas."""
        return super().meet_handle_rhs(s, JSONTypeArray._compute_array_meet)

    @staticmethod
    def _compute_array_meet(s1, s2):  # noqa: C901, PLR0912, PLR0915
        """Compute the meet of two array schemas ``s1`` and ``s2``."""
        if s2.type == "array":
            ret = JSONTypeArray({})
            ret.minItems = max(s1.minItems, s2.minItems)
            ret.maxItems = min(s1.maxItems, s2.maxItems)
            ret.uniqueItems = s1.uniqueItems or s2.uniqueItems

            def meet_array_items_dict_list(s1, s2, ret):
                if not (utils.is_dict(s1.items_) and utils.is_list(s2.items_)):
                    raise ValueError(
                        "Violating meet_array_items_dict_list condition: "
                        "'s1.items is dict' and 's2.items is list'"
                    )

                itms = []
                for i in s2.items_:
                    r = i.meet(s1.items_)
                    if not (is_bot(r) or r.is_uninhabited()):
                        itms.append(r)
                    else:
                        break

                ret.items_ = itms

                if is_top(s2.additionalItems):
                    ret.additionalItems = copy.deepcopy(s1.items_)
                elif is_bot(s2.additionalItems):
                    ret.additionalItems = False
                elif utils.is_dict(s2.additionalItems):
                    add_items = s2.additionalItems.meet(s1.items_)
                    ret.additionalItems = False if is_bot(add_items) else add_items
                return ret

            if utils.is_dict(s1.items_):
                if utils.is_dict(s2.items_):
                    ret.items_ = s1.items_.meet(s2.items_)

                elif utils.is_list(s2.items_):
                    ret = meet_array_items_dict_list(s1, s2, ret)

            elif utils.is_list(s1.items_):
                if utils.is_dict(s2.items_):
                    ret = meet_array_items_dict_list(s2, s1, ret)

                elif utils.is_list(s2.items_):
                    self_len = len(s1.items_)
                    s_len = len(s2.items_)

                    def meet_array_additional_items_list_list(s1, s2):
                        match (s1.additionalItems, s2.additionalItems):
                            case (bool(), bool()):
                                ad = s1.additionalItems and s2.additionalItems
                            case (JSONschema(), _):
                                ad = s1.additionalItems.meet(s2.additionalItems)
                            case (_, JSONschema()):
                                ad = s2.additionalItems.meet(s1.additionalItems)
                        return False if is_bot(ad) else ad

                    def meet_array_longlist_shorterlist(s1, s2, ret):
                        s1_len = len(s1.items_)
                        s2_len = len(s2.items_)
                        if s1_len <= s2_len:
                            raise ValueError(
                                "Violating meet_array_longlist_shorterlist "
                                "condition: 's1.len > s2.len'"
                            )
                        itms = []
                        for i, j in zip(s1.items_, s2.items_, strict=False):
                            r = i.meet(j)
                            if not (is_bot(r) or r.is_uninhabited()):
                                itms.append(r)
                            else:
                                ad = False
                                break
                        else:
                            for i in range(s2_len, s1_len):
                                r = s1.items_[i].meet(s2.additionalItems)
                                if not (is_bot(r) or r.is_uninhabited()):
                                    itms.append(r)
                                else:
                                    ad = False
                                    break
                            else:
                                ad = meet_array_additional_items_list_list(s1, s2)

                        ret.additionalItems = ad
                        ret.items_ = itms
                        return ret

                    if self_len == s_len:
                        itms = []
                        for i, j in zip(s1.items_, s2.items_, strict=False):
                            r = i.meet(j)
                            if not (is_bot(r) or r.is_uninhabited()):
                                itms.append(r)
                            else:
                                ad = False
                                break
                        else:
                            ad = meet_array_additional_items_list_list(s1, s2)

                        ret.additionalItems = ad
                        ret.items_ = itms

                    elif self_len > s_len:
                        ret = meet_array_longlist_shorterlist(s1, s2, ret)

                    elif self_len < s_len:
                        ret = meet_array_longlist_shorterlist(s2, s1, ret)
            ret.update_internal_state()
            return ret

        return JSONbot()

    def _is_subtype(self, s):
        """Return whether this array schema is a subtype of ``s``."""
        return super().is_subtype_handle_rhs(s, JSONTypeArray._compute_array_subtype)

    @staticmethod
    def _compute_array_subtype(s1, s2):  # noqa: C901, PLR0911, PLR0912, PLR0915
        """Return whether array schema ``s1`` is a subtype of array schema ``s2``."""
        if s2.type != "array":
            return False
        if s1.has_enum():
            return s1.subtype_enum(s2)
        #
        # -- minItems and maxItems
        is_sub_interval = s1.interval in s2.interval
        if not is_sub_interval:
            print_db("__01__")
            return False
        #
        # -- uniqueItems
        # An array with at most one item is trivially unique. Beyond that,
        # be conservative: a lhs allowing duplicates is not considered a
        # subtype of a rhs requiring uniqueness, even in subtle cases where
        # the lhs item schemas could never produce duplicates anyway.
        if s2.uniqueItems and not s1.uniqueItems and s1.maxItems > 1:
            print_db("__02__")
            return False
        #
        # -- items = {not empty}
        # no need to check additionalItems
        if utils.is_dict(s1.items_):
            if utils.is_dict(s2.items_):
                print_db(s1.items_)
                print_db(s2.items_)
                if s1.items_.is_subtype(s2.items_):
                    print_db("__05__")
                    return True
                print_db("__06__")
                return False
            if utils.is_list(s2.items_):
                if is_bot(s2.additionalItems):
                    print_db("__07__")
                    return False
                if is_top(s2.additionalItems):
                    for i in s2.items_:
                        if not s1.items_.is_subtype(i):
                            print_db("__08__")
                            return False
                    print_db("__09__")
                    return True
                if utils.is_dict(s2.additionalItems):
                    for i in s2.items_:
                        if not s1.items_.is_subtype(i):
                            print_db("__10__")
                            return False
                    print_db(type(s1.items_), s1.items_)
                    print_db(type(s2.additionalItems), s2.additionalItems)
                    if s1.items_.is_subtype(s2.additionalItems):
                        print_db("__11__")
                        return True
                    print_db("__12__")
                    return False
        elif utils.is_list(s1.items_):
            print_db("lhs is list")
            if utils.is_dict(s2.items_):
                if is_bot(s1.additionalItems):
                    for i in s1.items_:
                        if not i.is_subtype(s2.items_):
                            print_db("__13__")
                            return False
                    print_db("__14__")
                    return True
                if is_top(s1.additionalItems):
                    for i in s1.items_:
                        if not i.is_subtype(s2.items_):
                            return False
                    # since s1.additionalItems is top, top must also be
                    # a subtype of s2.items
                    return bool(JSONtop().is_subtype(s2.items_))
                if utils.is_dict(s1.additionalItems):
                    for i in s1.items_:
                        if not i.is_subtype(s2.items_):
                            return False
                    return bool(s1.additionalItems.is_subtype(s2.items_))
            # now lhs and rhs are lists
            elif utils.is_list(s2.items_):
                print_db("lhs & rhs are lists")
                len1 = len(s1.items_)
                len2 = len(s2.items_)
                for i, j in zip(s1.items_, s2.items_, strict=False):
                    if not i.is_subtype(j):
                        return False
                if len1 == len2:
                    print_db("len1 == len2")
                    if s1.additionalItems == s2.additionalItems:
                        return True
                    if is_top(s1.additionalItems) and is_bot(s2.additionalItems):
                        return False
                    if is_bot(s1.additionalItems) and is_top(s2.additionalItems):
                        return True
                    return s1.additionalItems.is_subtype(s2.additionalItems)
                if len1 > len2:
                    diff = len1 - len2
                    for i in range(len1 - diff, len1):
                        if is_bot(s2.additionalItems):
                            return False
                        if is_top(s2.additionalItems):
                            return True
                        if not s1.items_[i].is_subtype(s2.additionalItems):
                            print_db("9999")
                            return False
                    print_db("8888")
                    return True
                # len2 > len1
                diff = len2 - len1
                for i in range(len2 - diff, len2):
                    if is_bot(s1.additionalItems):
                        return True
                    if is_top(s1.additionalItems) or not s1.additionalItems.is_subtype(
                        s2.items_[i]
                    ):
                        return False
                return s1.additionalItems.is_subtype(s2.additionalItems)
        return None

    @staticmethod
    def neg(s):
        """Return the complement of an unconstrained array schema ``s``.

        Negating an array with item/length constraints is not supported and
        raises :class:`UnsupportedNegatedArray`.
        """
        if s.keys() & definitions.JtypesToKeywords["array"]:
            raise UnsupportedNegatedArray(schema=s)
        return bool_to_constructor["anyOf"](
            {"anyOf": get_default_types_except("array")}
        )


def _merge_with_meet(d1, d2):
    """Merge two key-to-schema dicts, meeting the schemas of shared keys."""
    result = {k: d1[k].meet(d2[k]) if k in d2 else d1[k] for k in d1}
    result.update({k: d2[k] for k in d2 if k not in d1})
    return result


class JSONTypeObject(JSONschema):
    """Schema for the JSON ``object`` type (properties, required keys, sizes)."""

    def __init__(self, s):
        super().__init__(s)
        self.type = self["type"] = "object"
        self.properties = self.get("properties", {})
        self.additionalProperties = self.get("additionalProperties", JSONtop())
        self.required = self.get("required", [])
        self.minProperties = self.get("minProperties", 0)
        self.maxProperties = self.get("maxProperties", portion.inf)
        self.patternProperties = {}
        if "patternProperties" in self:
            for k, v in self["patternProperties"].items():
                self.patternProperties[utils.regex_unanchor(k)] = v

    def compute_actual_min_max_properties(self):
        """Raise ``minProperties`` to at least the number of required keys."""
        new_min = max(self.minProperties, len(self.required))
        if new_min != self.minProperties:
            self.minProperties = new_min

    def _is_uninhabited(self):
        """Return whether the size bounds or required keys admit no object."""

        def required_is_uninhabited(s):
            """Check if a required key is not allowed by the key restrictions."""
            if s.additionalProperties:
                return False

            for k in s.required:
                if k not in s.properties:
                    for k_ in s.patternProperties:
                        if utils.regex_matches_string(k_, k):
                            break
                    else:
                        # here, inner loop finished and key was not found;
                        # so it is uninhabited because a required key is not allowed
                        return True

            return False

        return (
            self.minProperties > self.maxProperties
            or len(self.required) > self.maxProperties
            or required_is_uninhabited(self)
        )

    def update_internal_state(self):
        """Cache the size interval and normalize ``additionalProperties``."""
        self.compute_actual_min_max_properties()
        self.interval = portion.closed(self.minProperties, self.maxProperties)
        if (
            len(self.properties) == self.maxProperties
            or len(self.patternProperties) == self.maxProperties
            or (len(self.properties) + len(self.patternProperties))
            == self.maxProperties
        ):
            self.additionalProperties = False

    def _meet(self, s):
        """Meet with ``s``, intersecting sizes, required keys and property schemas."""
        return super().meet_handle_rhs(s, JSONTypeObject._compute_object_meet)

    @staticmethod
    def _compute_object_meet(s1, s2):
        """Compute the meet of two object schemas ``s1`` and ``s2``."""
        if s2.type == "object":
            ret = JSONTypeObject({})
            ret.required = list(set(s1.required).union(s2.required))
            ret.minProperties = max(s1.minProperties, s2.minProperties)
            ret.maxProperties = min(s1.maxProperties, s2.maxProperties)
            match (s1.additionalProperties, s2.additionalProperties):
                case (bool(), bool()):
                    ad = s1.additionalProperties and s2.additionalProperties
                case (JSONschema(), _):
                    ad = s1.additionalProperties.meet(s2.additionalProperties)
                case (_, JSONschema()):
                    ad = s2.additionalProperties.meet(s1.additionalProperties)
            ret.additionalProperties = False if is_bot(ad) else ad
            #
            # For meet of properties and patternProperties, no need to check
            # whether a key is valid against patternProperties of the other
            # schema or to calculate intersections among patternProperties of
            # both schemas cuz the validator takes care of this during
            # validation of actual instances. For efficiency, we just include
            # all keys in properties and patternProperties of both schemas.
            # We only have to handle exactly matching keys in both properties
            # and patternProperties.
            #
            ret.properties = _merge_with_meet(s1.properties, s2.properties)
            ret.patternProperties = _merge_with_meet(
                s1.patternProperties, s2.patternProperties
            )
            ret.update_internal_state()
            return ret
        return JSONbot()

    def _is_subtype(self, s):
        """Return whether this object schema is a subtype of ``s``."""
        return super().is_subtype_handle_rhs(s, JSONTypeObject._compute_object_subtype)

    @staticmethod
    def _compute_object_subtype(s1, s2):  # noqa: C901, PLR0911, PLR0912, PLR0915
        """The general intuition is that a json object with more keys is more
        restrictive than a similar object with fewer keys.

        E.g.: if corresponding keys have same schemas, then
        {name: {..}, age: {..}} <: {name: {..}}
        {name: {..}, age: {..}} />: {name: {..}}

        So the subtype checking is divided into two major parts:
        I) lhs keys/patterns/additional should be a superset of rhs
        II) schemas of comparable keys should have lhs <: rhs
        """
        if s2.type != "object":
            return False
        if s1.has_enum():
            return s1.subtype_enum(s2)
        # Check properties range
        is_sub_interval = s1.interval in s2.interval
        if not is_sub_interval:
            print_db(s1.interval, s1)
            print_db(s2.interval, s2)
            print_db("__00__")
            return False

        def get_schema_for_key(k, s):
            """Searches for matching key and get the corresponding schema(s).
            Returns iterable because if a key matches more than one pattern,
            that key schema has to match all corresponding patterns schemas.
            """
            if k in s.properties:
                return [s.properties[k]]
            # in case a key has to be checked against patternProperties,
            # it has to adhere to all schemas which have pattern matching the key.
            ret = [
                s.patternProperties[k_]
                for k_ in s.patternProperties
                if utils.regex_matches_string(k_, k)
            ]
            if ret:
                return ret

            return [s.additionalProperties]

        # Check that required keys satisfy subtyping.
        # lhs required keys should be superset of rhs required keys.
        if not set(s1.required).issuperset(s2.required):
            print_db("__02__")
            return False
        # If required keys are properly defined, check their corresponding
        # schemas and make sure they are subtypes.
        # This is required because you could have a required key which does not
        # have an explicit schema defined by the json object.

        for k in set(s1.required).intersection(s2.required):
            for lhs_ in get_schema_for_key(k, s1):
                for rhs_ in get_schema_for_key(k, s2):
                    if lhs_:
                        if rhs_:
                            if not lhs_.is_subtype(rhs_):
                                print_db(k, "LHS", lhs_, "RHS", rhs_)
                                print_db("!!__03__")
                                return False
                        else:
                            print_db("__04__")
                            return False

        extra_keys_on_rhs = set(s2.properties.keys()).difference(s1.properties.keys())
        for k in extra_keys_on_rhs.copy():
            if all(map(is_top, get_schema_for_key(k, s2))):
                extra_keys_on_rhs.remove(k)
                continue
            for k_ in s1.patternProperties:
                if utils.regex_matches_string(k_, k):
                    extra_keys_on_rhs.remove(k)
        for _k in extra_keys_on_rhs:
            if is_bot(s1.additionalProperties):
                continue
            if is_top(s1.additionalProperties):
                print_db("__06__")
                return False

        extra_patterns_on_rhs = set(s2.patternProperties.keys()).difference(
            s1.patternProperties.keys()
        )
        for k in extra_patterns_on_rhs.copy():
            for k_ in s1.patternProperties:
                if utils.regex_is_subset(k, k_):
                    extra_patterns_on_rhs.remove(k)
        if extra_patterns_on_rhs:
            if not s1.additionalProperties:
                print_db("__07__")
                return False
            for k in extra_patterns_on_rhs:
                if not s1.additionalProperties.is_subtype(s2.patternProperties[k]):
                    try:  # means regex k is infinite
                        parse(k).cardinality()
                    except OverflowError:
                        print_db("__08__")
                        return False

        # first, matching properties should be subtype pairwise
        unmatched_lhs_props_keys = set(s1.properties.keys())
        for k in s1.properties:
            if k in s2.properties:
                unmatched_lhs_props_keys.discard(k)
                if not s1.properties[k].is_subtype(s2.properties[k]):
                    return False
            else:
                # for keys without an exact match in rhs properties, check
                # against the rhs patternProperties matching the key
                for k_ in s2.patternProperties:
                    if utils.regex_matches_string(k_, k):
                        unmatched_lhs_props_keys.discard(k)
                        if not s1.properties[k].is_subtype(s2.patternProperties[k_]):
                            return False

        # second, matching patternProperties should be subtype pairwise
        unmatched_lhs_p_props_keys = set(s1.patternProperties.keys())
        for k in s1.patternProperties:
            for k_ in s2.patternProperties:
                if utils.regex_is_subset(k_, k):
                    unmatched_lhs_p_props_keys.discard(k)
                    if not s1.patternProperties[k].is_subtype(s2.patternProperties[k_]):
                        return False
        # third, lhs keys with no matching rhs properties or patternProperties
        # must satisfy rhs additionalProperties
        if is_top(s2.additionalProperties):
            return True
        if is_bot(s2.additionalProperties):
            return not (
                is_top(s1.additionalProperties)
                or unmatched_lhs_props_keys
                or unmatched_lhs_p_props_keys
            )
        for k in unmatched_lhs_props_keys:
            if not s1.properties[k].is_subtype(s2.additionalProperties):
                return False
        for k in unmatched_lhs_p_props_keys:
            if not s1.patternProperties[k].is_subtype(s2.additionalProperties):
                return False
        # fourth, lhs additionalProperties must be a subtype of
        # rhs additionalProperties
        if is_top(s1.additionalProperties):
            return False
        if is_bot(s1.additionalProperties):
            return True
        return s1.additionalProperties.is_subtype(s2.additionalProperties)

    @staticmethod
    def neg(s):
        """Return the complement of an unconstrained object schema ``s``.

        Negating an object with property/size constraints is not supported and
        raises :class:`UnsupportedNegatedObject`.
        """
        if s.keys() & definitions.JtypesToKeywords["object"]:
            raise UnsupportedNegatedObject(schema=s)
        return bool_to_constructor["anyOf"](
            {"anyOf": get_default_types_except("object")}
        )


def json_any_of_factory(s):
    """Build a schema from an ``anyOf`` by joining (unioning) its members."""
    ret = JSONbot()
    for i in s.get("anyOf", []):
        ret = ret.join(i)

    return ret


class JSONanyOf(JSONschema):
    """Schema representing a union (``anyOf``) of alternative schemas."""

    def __init__(self, s):
        super().__init__(s)
        self.type = "anyOf"
        self.anyOf: list = self["anyOf"]
        self.nonTrivialJoin = False
        # set on unions produced by negating a numeric schema: the schema
        # this union is the exact complement of
        self.complementOf: JSONschema | None = None

    def update_internal_state(self):
        """Flatten nested ``anyOf`` members into this union."""
        # Mutate self.anyOf in place: it is the same list object as
        # self["anyOf"], and rebinding the attribute would desync the two.
        while nested := [d_i for d_i in self.anyOf if "anyOf" in d_i]:
            for d_i in nested:
                self.anyOf.remove(d_i)
                self.anyOf.extend(d_i.get("anyOf", []))

    def _is_uninhabited(self):
        """Return whether every member of the union is uninhabited."""
        return all(is_bot(i) for i in self.anyOf)

    def _meet(self, s):
        """Meet with ``s`` by distributing the meet over the union members."""
        return super().meet_handle_rhs(s, JSONanyOf._meet_any_of)

    @staticmethod
    def _meet_any_of(s1, s2):
        """Meet each member of union ``s1`` with ``s2`` and rebuild the union."""
        anyofs = []
        for i in s1.anyOf:
            tmp = i.meet(s2)
            if not is_bot(tmp):
                anyofs.append(tmp)

        if len(anyofs) > 1:
            return JSONanyOf({"anyOf": anyofs})
        if len(anyofs) == 1:
            return anyofs.pop()
        return JSONbot()

    def _join(self, s):
        """Join ``s`` into the union, merging with a same-typed member if any."""
        if s.type == "anyOf":
            return json_any_of_factory({"anyOf": self.anyOf + s.anyOf})
        # the union grows, so it no longer is the recorded exact complement
        self.complementOf = None
        for i in self.anyOf:
            if i.type == s.type:
                t = i.join(s)
                if t.type != "anyOf":
                    # successful join, add new result and terminate
                    self.anyOf.remove(i)
                    self.anyOf.append(t)
                    break
        else:
            # loop exited normally without breaking
            # so add the single schema manually
            self.anyOf.append(s)
        return self

    def _is_subtype(self, s):
        """Return whether every member of this union is a subtype of ``s``."""

        def _is_anyof_subtype(s1, s2):
            for schema in s1.anyOf:
                if not schema.is_subtype(s2):
                    print_db("RHS in anyOf subtype", s2)
                    return False
            return True

        return _is_anyof_subtype(self, s)


def json_all_of_factory(s):
    """Build a schema from an ``allOf`` by meeting (intersecting) its members."""
    ret = JSONtop()
    for i in s.get("allOf", []):
        ret = ret.meet(i)

    return ret


type_to_constructor = {
    "string": JSONTypeString,
    "integer": JSONTypeInteger,
    "number": JSONTypeNumber,
    "boolean": JSONTypeBoolean,
    "null": JSONTypeNull,
    "array": JSONTypeArray,
    "object": JSONTypeObject,
}

bool_to_constructor = {"anyOf": json_any_of_factory, "allOf": json_all_of_factory}


def get_default_types_except(*args):
    """Return unconstrained schemas for every JSON type except those in ``args``."""
    return [
        type_to_constructor[t]({})
        for t in sorted(set(type_to_constructor.keys()).difference(args))
    ]
