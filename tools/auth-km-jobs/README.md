
# GHGA Auth Key Management Jobs

This repo contains the script that manages internal and external auth keys
and are executed as Kubernetes Jobs.

## Subcommands

You can run the following subcommands using `run <command name>`:

- `refresh-int-keys`: Recreate internal signing keys and store them in the vault
- `refresh-ext-keys`: Refetch external public key set and store it in the vault
- `refresh-all-keys`: Refresh both internal and external keys in the vault

## Environment variables

The following environment variables are evaluated:

- `VAULT_ADDR`: the address of the vault server
- `VAULT_TOKEN`: token for allowing write access to the vault server
- `VAULT_NAMESPACE`: vault namespace (None by default)

## Vault paths

The following vault paths are used:

- `auth/priv`: private keys
- `auth/pub/int`: public keys (internal)
- `auth/pub/ext`: public keys (external)
