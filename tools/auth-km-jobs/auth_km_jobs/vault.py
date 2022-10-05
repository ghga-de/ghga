"""Vault management"""

import os

import hvac

DEFAULT_ADDR = "http://localhost:8200"
DEFAULT_NAMESPACE = None
DEFAULT_TOKEN = "dev-token"
DEFAULT_KEY = "data"

PATH_PRIVATE = "auth/priv"
PATH_PUBLIC_INTERNAL = "auth/pub/int"
PATH_PUBLIC_EXTERNAL = "auth/pub/ext"


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
        # cert=(client_cert_path, client_key_path),
        # verify=server_cert_path,
    )


def store_in_vault(path: str, value: str):
    """Store a string value under they given path."""
    vault = get_vault()

    create_response = vault.secrets.kv.create_or_update_secret(
        path=path, secret={DEFAULT_KEY: value}
    )
    if is_dev():
        read_response = vault.secrets.kv.read_secret_version(path=path)
        read_value = read_response["data"]["data"][DEFAULT_KEY]
        assert read_value == value
    return create_response


def store_private_key(key: str):
    """Store the private key as JSON value."""
    return store_in_vault(PATH_PRIVATE, key)


def store_internal_public_key(key: str):
    """Store the internal public key as JSON value."""
    return store_in_vault(PATH_PUBLIC_INTERNAL, key)


def store_external_public_key(key: str):
    """Store the external public key as JSON value."""
    if is_dev():
        print(key)
    return store_in_vault(PATH_PUBLIC_INTERNAL, key)
