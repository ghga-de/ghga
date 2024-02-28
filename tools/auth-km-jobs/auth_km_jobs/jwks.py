"""JSON Web Key Management"""

import httpx
from jwcrypto import jwk

from .config import Config

config = Config()


def fetch_external_jwks() -> str:
    """Fetch the JSON string with the external JWKS."""
    config_response = httpx.get(config.discovery_url, timeout=config.timeout)
    config_dict = config_response.json()
    if not isinstance(config_dict, dict) or "version" not in config_dict:
        raise ValueError("Unexpected discovery object")
    jwks_uri = config_dict.get("jwks_uri")
    if not jwks_uri or not isinstance(jwks_uri, str):
        raise ValueError("Cannot discover JWKS URI")
    if not jwks_uri.startswith(config.oidc_authority_url):
        raise ValueError("Unexpected JWKS URI")
    jwks_response = httpx.get(jwks_uri, timeout=config.timeout)
    jwks_dict = jwks_response.json()
    if not isinstance(jwks_dict, dict) or "keys" not in jwks_dict:
        raise ValueError("Unexpected JWKS object")
    return jwks_response.text


def generate_internal_jwk() -> str:
    """Generate a JSON string with a new key pair."""
    return jwk.JWK.generate(kty="EC", crv="P-256")
