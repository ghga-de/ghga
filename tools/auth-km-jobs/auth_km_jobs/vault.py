"""Vault management"""

import os

import hvac

DEFAULT_ADDR = "http://localhost:8200"
DEFAULT_NAMESPACE = "vault"
DEFAULT_TOKEN = "dev-token"
DEFAULT_KEY = "data"

PATH_INT_PRIVATE = "auth/priv/int"
PATH_INT_PUBLIC = "auth/pub/int"
PATH_EXT_PUBLIC = "auth/pub/ext"
PATH_WPS_PRIVATE = "auth/priv/wps"
PATH_WPS_PUBLIC = "auth/pub/wps"

VERIFY_WRITE = True  # read back from vault and compare
SHOW_EXTERNAL_KEYS = True  # print public key set

SSL_VERIFY = False  # could also be path to the certificate
TIMEOUT = 15  # timeout in seconds


def env(name: str, default=None) -> str:
    """Get an environment variable"""
    return os.environ.get(name, default)


def is_dev():
    """Check whether this is the dev environment"""
    return env("VAULT_TOKEN") == "dev-token"


def get_vault() -> hvac.Client:
    """Get HashiCorp Vault client."""
    url = env("VAULT_ADDR", DEFAULT_ADDR)
    namespace = env("VAULT_NAMESPACE", DEFAULT_NAMESPACE)
    token = env("VAULT_TOKEN", DEFAULT_TOKEN)
    return hvac.Client(
        url=url,
        namespace=namespace,
        token=token,
        verify=SSL_VERIFY,
        timeout=TIMEOUT,
    )


def store_in_vault(path: str, value: str):
    """Store a string value under they given path."""
    vault = get_vault()

    create_response = vault.secrets.kv.create_or_update_secret(
        path=path, secret={DEFAULT_KEY: value}
    )
    if VERIFY_WRITE:
        read_response = vault.secrets.kv.read_secret_version(path=path)
        read_value = read_response["data"]["data"][DEFAULT_KEY]
        if read_value != value:
            print("ERROR: Could not read back the stored value.")
            print("Create response:", create_response)
            print("Read response:", read_response)
    return create_response


def store_private_int_key(key: str):
    """Store the private internal auth key as JSON value."""
    return store_in_vault(PATH_INT_PRIVATE, key)


def store_public_int_key(key: str):
    """Store the public internal auth key as JSON value."""
    return store_in_vault(PATH_INT_PUBLIC, key)


def store_public_ext_key(key: str):
    """Store the public external (OIDC) auth key set as JSON value."""
    if SHOW_EXTERNAL_KEYS:
        print("External auth key set:", key)
    return store_in_vault(PATH_EXT_PUBLIC, key)


def store_private_wps_key(key: str):
    """Store the private work package signing key as JSON value."""
    return store_in_vault(PATH_WPS_PRIVATE, key)


def store_public_wps_key(key: str):
    """Store the public work package validation key as JSON value."""
    return store_in_vault(PATH_WPS_PUBLIC, key)
