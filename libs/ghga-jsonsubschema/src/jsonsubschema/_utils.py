"""Utility functions for JSON Schema processing.

Originally created on May 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import fractions
import functools
import json
import math
import numbers
import re
import sys

import jsonschema
import portion
from greenery import parse

import jsonsubschema._constants as definitions
from jsonsubschema import config


def is_str(i):
    """Return whether ``i`` is a string."""
    return isinstance(i, str)


def is_int(i):
    """Return whether ``i`` is an integer (but not a boolean)."""
    if isinstance(i, bool):
        return False
    return isinstance(i, int)


def is_int_equiv(i):
    """Return whether ``i`` is an integer or a float with no fractional part."""
    if isinstance(i, bool):
        return False
    return isinstance(i, int) or (isinstance(i, float) and float(i).is_integer())


def is_num(i):
    """Return whether ``i`` is a number (but not a boolean)."""
    if isinstance(i, bool):
        return False
    return isinstance(i, numbers.Number)


def is_list(i):
    """Return whether ``i`` is a list."""
    return isinstance(i, list)


def is_dict(i):
    """Return whether ``i`` is a dict."""
    return isinstance(i, dict)


def validate_schema(s):
    """Validate ``s`` against the configured JSON Schema validator draft."""
    return config.VALIDATOR.check_schema(s)


@functools.lru_cache
def _instance_validator(validator):
    """Return ``validator`` with ``integer`` matching int-equivalent floats.

    The subtype checker treats numbers mathematically, so a float without a
    fractional part (e.g. ``10.0``) counts as an integer even though the
    draft 4 validator would reject it for ``{"type": "integer"}``.
    """
    return jsonschema.validators.extend(
        validator,
        type_checker=validator.TYPE_CHECKER.redefine(
            "integer", lambda _checker, instance: is_int_equiv(instance)
        ),
    )


def get_valid_enum_vals(enum, s):
    """Return the enum values that validate against the schema ``s``.

    The values are validated with the configured validator draft so that
    keywords keep their intended semantics (``jsonschema.validate`` would
    guess the draft from the schema and default to the latest one).
    """
    validator = _instance_validator(config.VALIDATOR)(dict(s))
    return [i for i in enum if validator.is_valid(i)]


def get_typed_enum_vals(enum, t):
    """Return the enum values whose Python type matches the JSON type ``t``."""
    if t == "integer":
        enum = (i for i in enum if not isinstance(i, bool))
    return [i for i in enum if isinstance(i, definitions.JtypesToPyTypes[t])]


def print_db(*args):
    """Print debugging output, but only when debug mode is enabled in config."""
    if config.PRINT_DB:
        if args:
            print("".join(str(arg) + " " for arg in args))
        else:
            print()


#
# To avoid regex bottlenecks, instead of using '.*' as the default value
# for string.pattern, we use 'None' and apply explicit checks for 'None'.
# E.g. regex_meet(s1, None) = s1
#


def prepare_pattern_for_greenry(s):
    r"""The greenery library we use for regex intersection assumes
    patterns are unanchored by default. Anchoring chars ^ and $ are
    treated as literals by greenery.
    So basically strip any non-escaped ^ and $ when using greenery.
    Moreover, for any escaped ^ or $, we remove the \ to adhere to
    greenery syntax (when they are escaped, they are literals).
    """
    s = re.sub(
        r"(?<!\\|\[)((?:\\{2})*)\^", r"\g<1>", s
    )  # strip non-escaped ^ that is not inside []
    s = re.sub(r"(?<!\\)((?:\\{2})*)\$", r"\g<1>", s)  # strip non-escaped $
    s = re.sub(r"(?<!\\)((?:\\{1})*)\\\^", r"\g<1>^", s)  # strip \ before ^
    return re.sub(r"(?<!\\)((?:\\{1})*)\\\$", r"\g<1>$", s)  # strip \ before $


def regex_unanchor(p):
    """Convert a JSON (unanchored) regex into the anchored form greenery expects.

    JSON regexes are not anchored by default while the regex library we use
    assumes the opposite: regexes are anchored by default AND ^ and $ are
    literals and don't carry their anchoring meaning. So pad the pattern with
    ``.*`` on any side that is not already anchored and drop the anchors.
    """
    if p:
        if p[0] == "^":
            p = p[1:]
        elif p[:2] != ".*":
            p = ".*" + p
        if p[-1] == "$":
            p = p[:-1]
        elif p[-2:] != ".*":
            p = p + ".*"
    return p


def regex_matches_string(regex=None, s=None):
    """Return whether ``s`` matches ``regex`` (an empty ``regex`` matches anything)."""
    if regex:
        return parse(regex).matches(s)
    return True


def regex_meet(s1, s2):
    """Return the intersection of two regex patterns, or ``None`` if it is empty.

    An empty operand acts as "match anything", so the meet reduces to the other
    operand in that case.
    """
    if s1 and s2:
        ret = parse(s1) & parse(s2)
        return str(ret.reduce()) if not ret.empty() else None
    if s1:
        return s1
    if s2:
        return s2
    return None


def regex_is_subset(s1, s2):
    """Regex subset is quite expensive to compute
    especially for complex patterns.
    """
    if s1 and s2:
        s1 = parse(s1).reduce()
        s2 = parse(s2).reduce()
        try:
            s1.cardinality()
            s2.cardinality()
            return set(s1.strings()).issubset(s2.strings())
        except OverflowError:
            # catching a general exception thrown from greenery
            # see https://github.com/qntm/greenery/blob/master/greenery/lego.py
            # ... raise Exception("Please choose an 'otherchar'")
            return s1.equivalent(s2) or (s1 & s2.everythingbut()).empty()
        except Exception as e:
            exit_with_msg("regex failure from greenry", e)
    elif s1:
        return True
    elif s2:
        return parse(s2).equivalent(parse(".*"))
    return None


def string_range_to_regex(min, max):
    """Return a regex matching strings whose length lies in ``[min, max]``."""
    if min > max:
        raise ValueError(f"min ({min}) must be <= max ({max})")
    if min == max:
        pattern = ".{" + str(min) + "}"  # '.{min}'
    elif max == portion.inf:
        pattern = ".{" + str(min) + ",}"  # '.{min,}'
    else:
        pattern = ".{" + str(min) + "," + str(max) + "}"  # '.{min, max}'

    return pattern


def complement_of_string_pattern(s):
    """Return a regex matching exactly the strings not matched by ``s``."""
    return str(parse(s).everythingbut().reduce())


def lcm(x, y):
    """Return the least common multiple of ``x`` and ``y``.

    ``None`` operands are treated as absent; the result is then the other
    operand (or ``None`` if both are absent).
    """
    bad_values = [
        None,
    ]  # portion.inf, -portion.inf]
    if x in bad_values:
        if y in bad_values:
            return None
        return y
    if y in bad_values:
        return x
    if is_int(x) and is_int(y):
        return x * y / math.gcd(int(x), int(y))
    return x * y / float_gcd(x, y)


def gcd(x, y):
    """Return the greatest common divisor of ``x`` and ``y``.

    Returns ``None`` if either operand is absent (``None``).
    """
    bad_values = [
        None,
    ]  # portion.inf, -portion.inf, None]
    if x in bad_values or y in bad_values:
        return None
    if is_int(x) and is_int(y):
        return math.gcd(int(x), int(y))
    return float_gcd(x, y)


def float_gcd(a, b):
    """Return an approximate greatest common divisor of two floats.

    ``fractions.gcd`` used to kind-of-work but was removed in Python 3.9 and
    ``math.gcd`` only supports integers. This reuses the old ``fractions.gcd``
    logic but refines it by re-interpreting the floats as fractions. This is
    far from perfect but gives the expected result in more cases.
    """
    fa = fractions.Fraction(str(a))
    fb = fractions.Fraction(str(b))
    while fb:
        fa, fb = fb, fa % fb
    return float(fa)


def generate_range_with_multiple_of_or(range_, pos_mul_of):
    """Yield the values in ``range_`` divisible by any factor in ``pos_mul_of``.

    With no factors given, all values in ``range_`` are yielded.
    """
    if pos_mul_of:
        for i in range_:
            if any(i % k == 0 for k in pos_mul_of):
                yield i
    else:
        for i in range_:
            yield i


def generate_range_with_not_multiple_of_and(range_, neg_mul_of):
    """Yield the values in ``range_`` divisible by none of ``neg_mul_of``.

    With no factors given, all values in ``range_`` are yielded.
    """
    if neg_mul_of:
        for i in range_:
            if all(i % k != 0 for k in neg_mul_of):
                yield i
    else:
        for i in range_:
            yield i


def generate_range_with_multipleof(range_, pos, neg):
    """Yield ``range_`` values divisible by a ``pos`` and no ``neg`` factor."""
    return generate_range_with_not_multiple_of_and(
        generate_range_with_multiple_of_or(range_, pos), neg
    )


def get_new_min_max_with_mulof(mn, mx, mulof):
    """Tighten a ``[mn, mx]`` range to its smallest/largest multiples of ``mulof``.

    At the moment, this is part of an enumerative solution for ``multipleOf``
    on integers. Is there a more efficient way to find, for ``x <= n <= y``,
    the smallest ``x_min > x`` such that ``x_min % f == 0`` and the largest
    ``y_max < y`` such that ``x_max % f == 0`` for some factor ``f``?
    """
    if is_num(mulof) and mulof < mx:
        if is_num(mn):
            while mn % mulof != 0:
                mn = mn + 1
        if is_num(mx):
            while mx % mulof != 0:
                mx = mx - 1
    return mn, mx


def is_interval_finite(i):
    """Return whether the interval ``i`` has finite lower and upper bounds."""
    return is_num(i.lower) and is_num(i.upper)


def are_intervals_mergable(i1, i2):
    """Return whether intervals ``i1`` and ``i2`` overlap or are adjacent."""
    return (
        i1.overlaps(i2)
        or (is_num(i1.lower) and is_num(i2.upper) and i1.lower - i2.upper == 1)
        or (is_num(i2.lower) and is_num(i1.upper) and i2.lower - i1.upper == 1)
    )


def interval_contains_integer(i):
    """Return whether the interval ``i`` contains at least one integer value."""
    for atom in i:
        if not is_num(atom.lower) or not is_num(atom.upper):
            # a non-empty unbounded interval always contains integers
            return True
        n = math.ceil(atom.lower)
        if n == atom.lower and atom.left == portion.OPEN:
            n += 1
        if n < atom.upper or (n == atom.upper and atom.right == portion.CLOSED):
            return True
    return False


def interval_contains_multiple_of(i, mulof):
    """Return whether the interval ``i`` contains a multiple of ``mulof``.

    The bounds are converted to fractions so that divisibility is decided
    exactly instead of with floating point arithmetic.
    """
    step = fractions.Fraction(str(mulof))
    for atom in i:
        if not is_num(atom.lower) or not is_num(atom.upper):
            # a non-empty unbounded interval contains multiples of any factor
            return True
        multiple = math.ceil(fractions.Fraction(str(atom.lower)) / step) * step
        if multiple == atom.lower and atom.left == portion.OPEN:
            multiple += step
        upper = fractions.Fraction(str(atom.upper))
        if multiple < upper or (multiple == upper and atom.right == portion.CLOSED):
            return True
    return False


def integer_valued_multiple_step(mulof):
    """Return the spacing between the integer-valued multiples of ``mulof``.

    For ``mulof = p/q`` in lowest terms, a multiple ``k * mulof`` is an
    integer exactly when ``q`` divides ``k``, so the integer-valued multiples
    of ``mulof`` are precisely the multiples of the numerator ``p``.
    """
    return fractions.Fraction(str(mulof)).numerator


def interval_diff_is_integer_points(i1, i2):
    """Return whether ``i1`` minus ``i2`` contains only single integer points."""
    for atom in i1 - i2:
        if atom.lower != atom.upper or not is_int_equiv(atom.lower):
            return False
    return True


def load_json_file(path, msg=None):
    """Load and return the JSON content of the file at ``path``.

    On failure, print ``msg`` together with the exception and exit.
    """
    with open(path) as fh:
        try:
            return json.load(fh)
        except Exception as e:
            exit_with_msg(msg, e)


def exit_with_msg(msg, e=None):
    """Print ``msg`` (and the optional exception ``e``) and exit with status 1."""
    print("Message:", msg, ";", "Exception:", e)
    sys.exit(1)
