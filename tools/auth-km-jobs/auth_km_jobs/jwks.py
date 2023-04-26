"""JSON Web Key Management"""

import httpx
from jwcrypto import jwk

OIDC_AUTHORITY_URL = "https://proxy.aai.lifescience-ri.eu/"

DISCOVERY_URL = f"{OIDC_AUTHORITY_URL}.well-known/openid-configuration"

TIMEOUT = 30  # timeout in seconds


def fetch_external_jwks() -> str:
    """Fetch the JSON string with the external JWKS."""
    config_respsonse = httpx.get(DISCOVERY_URL, timeout=TIMEOUT)
    config_dict = config_respsonse.json()
    if not isinstance(config_dict, dict) or "version" not in config_dict:
        raise ValueError("Unexpected discovery object")
    jwks_uri = config_dict.get("jwks_uri")
    if not jwks_uri or not isinstance(jwks_uri, str):
        raise ValueError("Cannot discover JWKS URI")
    if not jwks_uri.startswith(OIDC_AUTHORITY_URL):
        raise ValueError("Unexpected JWKS URI")
    jwks_response = httpx.get(jwks_uri, timeout=TIMEOUT)
    jwks_dict = jwks_response.json()
    if not isinstance(jwks_dict, dict) or "keys" not in jwks_dict:
        raise ValueError("Unexpected JWKS object")
    return jwks_response.text


def generate_internal_jwk() -> str:
    """Generate a JSON string with a new key pair."""
    return jwk.JWK.generate(kty="EC", crv="P-256")
