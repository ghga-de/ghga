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

"""Module that provides secret vericication codes."""

import hashlib
import os
import random
import secrets
import string

CODE_DIGITS = "".join(sorted(set(string.digits) - set("01")))
CODE_LETTERS = "".join(sorted(set(string.ascii_uppercase) - set("OI")))
CODE_CHARS = CODE_LETTERS + CODE_DIGITS
SALT_CHARS = string.ascii_uppercase + string.digits

CODE_SIZE = 6
SALT_SIZE = 16

__all__ = [
    "generate_code",
    "hash_code",
    "validate_code",
]


def generate_code(size: int = CODE_SIZE) -> str:
    """Generate a random verification code.

    The code consists of 6 uppercase letters and digits without ambiguous characters.
    Also, the code is guaranteed to contain at least 2 digits and 2 letters.
    Other code sizes are possible, with the same relative amount of digits and letters.
    """
    choice = secrets.choice
    code_chars: list[str] = []
    append = code_chars.append
    num_digits = num_letters = size // 3
    for _ in range(num_letters):
        append(choice(CODE_LETTERS))
    for _ in range(num_digits):
        append(choice(CODE_DIGITS))
    for _ in range(size - num_digits - num_letters):
        append(choice(CODE_CHARS))
    random.shuffle(code_chars)
    return "".join(code_chars)


def _generate_salt(size: int = SALT_SIZE) -> str:
    """Generate a random salt."""
    return os.urandom(size // 2).hex()


def _hash_verification_code_with_salt(code: str, salt: str) -> str:
    """Hash a verification code with a given salt."""
    salted_code = salt + code
    return hashlib.sha256(salted_code.encode()).hexdigest()


def hash_code(code: str, salt_size=SALT_SIZE) -> str:
    """Hash a verification code with a random salt."""
    code = code.upper()  # make sure the code uses only upper case
    salt = _generate_salt(salt_size)
    hash = _hash_verification_code_with_salt(code, salt)
    return salt + hash


def validate_code(code: str, hash_with_salt: str, salt_size=SALT_SIZE) -> bool:
    """Validate a verification code against a stored hash with salt."""
    code = code.upper()  # allow users to enter lower case letters instead of upper case
    salt, hash = hash_with_salt[:salt_size], hash_with_salt[salt_size:]
    return hash == _hash_verification_code_with_salt(code, salt)
