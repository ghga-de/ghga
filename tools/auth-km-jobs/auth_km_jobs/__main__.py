import typer

from .jwks import fetch_external_jwks, generate_internal_jwk
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
    print("The workd package service key pair has been stored.")


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


if __name__ == "__main__":
    app()
