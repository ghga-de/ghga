"""Main script for managing keys."""

import typer

from .c4gh import generate_crypt4gh_key_pair
from .jwks import fetch_external_jwks, generate_internal_jwk
from .tokens import generate_simple_token
from .vault import (
    store_private_int_key,
    store_public_int_key,
    store_public_ext_key,
    store_private_wps_key,
    store_public_wps_key,
)

app = typer.Typer()


@app.command()
def refresh_int_keys():
    """Refresh the internal auth token signing key pair."""
    print("Generating a new internal auth key pair...")
    key = generate_internal_jwk()
    store_private_int_key(key.export_private())
    store_public_int_key(key.export_public())
    print("The internal auth key pair has been stored.")


@app.command()
def refresh_wps_keys():
    """Refresh the work package signing key pair."""
    print("Generating a new work package service key pair...")
    key = generate_internal_jwk()
    store_private_wps_key(key.export_private())
    store_public_wps_key(key.export_public())
    print("The work package service key pair has been stored.")


@app.command()
def refresh_ext_keys():
    """Refresh the external (OIDC) auth key set."""
    print("Fetching the current external auth key set...")
    keys = fetch_external_jwks()
    store_public_ext_key(keys)
    print("The external auth key set has been stored.")


@app.command()
def refresh_all_keys():
    """Refresh all token signing keys."""
    first_error = None
    for cmd in (
        refresh_int_keys,
        refresh_wps_keys,
        refresh_ext_keys,
    ):
        try:
            cmd()
        except Exception as error:  # pylint: disable=broad-except
            print("ERROR:", error)
            if not first_error:
                first_error = error
    if first_error:
        print("Could not run all commands, raising the first error:")
        raise first_error


@app.command()
def generate_test_keys(num_jwk: int =1, num_c4gh: int =1, num_tokens: int = 1):
    """Generate and print cryptographic values for testing.
    
    You can specify any number of JSON Web Keys, Crypt4GH keys
    and simple tokens that shall be generated and printed out.
    """
    for n_jwk in range(1, num_jwk + 1):
        name = "JWK"
        if num_jwk > 1:
            name += f"_{n_jwk}"
        key = generate_internal_jwk()
        print(f"{name}_PRIV='{key.export_private()}'")
        print(f"{name}_PUB='{key.export_public()}'")
    for n_c4gh in range(1, num_c4gh + 1):
        name = "C4GH"
        if num_c4gh > 1:
            name += f"_{n_c4gh}"
        key = generate_crypt4gh_key_pair()
        print(f"{name}_PRIV={key.export_private()}")
        print(f"{name}_PUB={key.export_public()}")
    for n_token in range(1, num_tokens + 1):
        name = "TOKEN"
        if num_tokens > 1:
            name += f"_{n_token}"
        token = generate_simple_token()
        print(f"{name}={token.token}")
        print(f"{name}_HASH={token.hash}")


if __name__ == "__main__":
    app()
