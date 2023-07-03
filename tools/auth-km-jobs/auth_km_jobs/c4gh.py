import base64

from nacl.public import PrivateKey

__all__ = ["generate_crypt4gh_key_pair", "Crypt4GHKeyPair"]


class Crypt4GHKeyPair:
    """A Curve25519 key pair as used in Crypt4GH."""

    def __init__(self, key: PrivateKey):
        """Initialize with PrivateKey instance."""
        self.key = key

    def export_private(self) -> str:
        """Export private key as base64 encoded string."""
        return encode_key(bytes(self.key))

    def export_public(self) -> str:
        """Export public key as base64 encoded string."""
        return encode_key(bytes(self.key.public_key))


def generate_crypt4gh_key_pair() -> Crypt4GHKeyPair:
    """Generate a Curve25519 key pair as used in Crypt4GH."""
    return Crypt4GHKeyPair(PrivateKey.generate())


def encode_key(key: bytes) -> str:
    """Base64 encode a private or public key."""
    return base64.b64encode(key).decode("ascii")
