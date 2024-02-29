"""Vault management"""

import hvac
from hvac.api.auth_methods import Kubernetes

from .config import Config

# Load configuration
config = Config()


def get_vault() -> hvac.Client:
    """Get HashiCorp Vault client."""
    url = config.vault_addr
    namespace = config.vault_namespace
    role = config.kube_role
    if role:
        jwt = open(config.sa_token_path).read()
        token = None
    else:
        jwt = None
        token = config.token

    client = hvac.Client(
        url=url,
        token=token,
        verify=config.ssl_verify,
        timeout=config.timeout,
        namespace=namespace,
    )

    if role:
        Kubernetes(client.adapter).login(role=role, jwt=jwt)

    return client


def store_in_vault(path: str, value: str):
    """Store a string value under they given path."""
    vault = get_vault()
    create_response = vault.secrets.kv.create_or_update_secret(
        path=path,
        secret={config.secret_key_name: value},
        mount_point=config.mount_point,
    )
    if config.verify_write:
        read_response = vault.secrets.kv.read_secret_version(
            path=path, mount_point=config.mount_point
        )
        read_value = read_response["data"]["data"][config.secret_key_name]
        if read_value != value:
            print("ERROR: Could not read back the stored value.")
            print("Create response:", create_response)
            print("Read response:", read_response)
    return create_response


def store_private_int_key(key: str):
    """Store the private internal auth key as JSON value."""
    return store_in_vault(config.path_prefix + config.path_int_private, key)


def store_public_int_key(key: str):
    """Store the public internal auth key as JSON value."""
    return store_in_vault(config.path_prefix + config.path_int_public, key)


def store_public_ext_key(key: str):
    """Store the public external (OIDC) auth key set as JSON value."""
    if config.show_external_keys:
        print("External auth key set:", key)
    return store_in_vault(config.path_prefix + config.path_ext_public, key)


def store_private_wps_key(key: str):
    """Store the private work package signing key as JSON value."""
    return store_in_vault(config.path_prefix + config.path_wps_private, key)


def store_public_wps_key(key: str):
    """Store the public work package validation key as JSON value."""
    return store_in_vault(config.path_prefix + config.path_wps_public, key)
