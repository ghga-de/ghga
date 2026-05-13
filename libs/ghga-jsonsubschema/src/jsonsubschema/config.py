"""Configuration settings and flags for jsonsubschema.

Originally created on June 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import jsonschema

VALIDATOR = jsonschema.Draft4Validator  # Which schema validator draft to use
PRINT_DB = False  # Print debugging info?
WARN_UNINHABITED = False  # Enable uninhabited types warning?


# API to set which schema validator draft to use
def set_json_validator_version(v=jsonschema.Draft4Validator):
    """Currently, our subtype checking supports json schema draft 4 only,
    so VALIDATOR should not changed.
    We prodive the method for future support of other json schema versions.
    """
    global VALIDATOR
    VALIDATOR = v


# API to set print debugging info?
def set_debug(b=False):
    """Enable or disable debug output."""
    global PRINT_DB
    PRINT_DB = bool(b)


# API to enable uninhabited types warning?
def set_warn_uninhabited(b=False):
    """Enable or disable warnings for uninhabited schema types."""
    global WARN_UNINHABITED
    WARN_UNINHABITED = bool(b)
