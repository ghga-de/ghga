"""Vault management"""

import os

import hvac

DEFAULT_ADDR = "http://localhost:8200"
DEFAULT_NAMESPACE = "vault"
DEFAULT_TOKEN = "dev-token"
DEFAULT_KEY = "data"

PATH_PRIVATE = "auth/priv"
PATH_PUBLIC_INTERNAL = "auth/pub/int"
PATH_PUBLIC_EXTERNAL = "auth/pub/ext"

VERIFY_WRITE = True  # read back from vault and compare
SHOW_PUBLIC_KEY = True  # print public key

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


def store_private_key(key: str):
    """Store the private key as JSON value."""
    return store_in_vault(PATH_PRIVATE, key)


def store_internal_public_key(key: str):
    """Store the internal public key as JSON value."""
    return store_in_vault(PATH_PUBLIC_INTERNAL, key)


def store_external_public_key(key: str):
    """Store the external public key as JSON value."""
    if SHOW_PUBLIC_KEY:
        print(key)
    return store_in_vault(PATH_PUBLIC_INTERNAL, key)
