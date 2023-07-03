from hashlib import sha256
from secrets import token_urlsafe
from typing import NamedTuple

__all__ = ["generate_simple_token", "SimpleToken"]


class SimpleToken(NamedTuple):
    """A simple token together with its hashed value."""

    token: str
    hash: str


def generate_simple_token(length: int =32) -> SimpleToken:
    """Generate a random simple token of the given length."""

    token = token_urlsafe(length)
    token_hash = sha256(token.encode()).hexdigest()

    return SimpleToken(token, token_hash)
