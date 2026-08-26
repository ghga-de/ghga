"""Configuration settings and flags for jsonsubschema.

Originally created on June 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import jsonschema

__all__ = [
    "set_debug",
    "set_json_validator_version",
    "set_warn_uninhabited",
]

VALIDATOR = jsonschema.Draft4Validator  # Which schema validator draft to use
PRINT_DB = False  # Print debugging info?
WARN_UNINHABITED = False  # Enable uninhabited types warning?


def set_json_validator_version(v=jsonschema.Draft4Validator):
    """Set which JSON Schema validator draft to use.

    Currently, our subtype checking supports JSON Schema draft 4 only, so
    ``VALIDATOR`` should not be changed. We provide this method for future
    support of other JSON Schema versions.
    """
    global VALIDATOR
    VALIDATOR = v


def set_debug(b=False):
    """Enable or disable debug output."""
    global PRINT_DB
    PRINT_DB = bool(b)


def set_warn_uninhabited(b=False):
    """Enable or disable warnings for uninhabited schema types."""
    global WARN_UNINHABITED
    WARN_UNINHABITED = bool(b)
