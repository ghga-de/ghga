import typer

from .jwks import fetch_external_jwks, generate_internal_jwk
from .vault import (
    store_private_key,
    store_internal_public_key,
    store_external_public_key,
)

app = typer.Typer()


@app.command()
def refresh_ext_keys():
    """Refresh the external auth key set."""
    print("Fetching the current external key set...")
    keys = fetch_external_jwks()
    store_external_public_key(keys)
    print("The external key set has been stored.")


@app.command()
def refresh_int_keys():
    """Create the internal auth key pair."""
    print("Generating a new internal key pair...")
    key = generate_internal_jwk()
    store_private_key(key.export_private())
    store_internal_public_key(key.export_public())
    print("The internal key pair has been stored.")


@app.command()
def refresh_all_keys():
    """Refresh all auth signing keys."""
    first_error = None
    for cmd in refresh_int_keys, refresh_ext_keys:
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
