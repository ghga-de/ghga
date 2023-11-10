
# GHGA Auth Key Management Jobs

This repo contains the script that manages JWT signing keys used by GHGA.

This script can be executed as a Kubernetes Job, either regularly or on demand.

## Subcommands

The following subcommands can be executed using `run <command name>`:

- `refresh-int-keys`: Recreate internal auth token signing keys and store them in the vault
- `refresh-wps-keys`: Recreate internal work package signing keys and store them in the vault
- `refresh-ext-keys`: Refetch the external auth (OIDC) public key set and store it in the vault
- `refresh-all-keys`: Refresh all internal and external token signing keys in the vault

## Environment variables

The following environment variables are evaluated:

- `VAULT_ADDR`: the address of the vault server
- `VAULT_TOKEN`: token for allowing write access to the vault server
- `VAULT_NAMESPACE`: vault namespace ("vault" by default)
- `AUTH_KM_KUBE_ROLE`: name of the role used to authenticate to Vault

## Vault paths

The following vault paths are used:

- `auth/priv/int`: private keys for internal auth tokens
- `auth/pub/int`: public keys for internal auth tokens
- `auth/pub/ext`: public keys for external (OIDC) auth tokens
- `auth/priv/wps`: private keys for signing work package tokens
- `auth/pub/wps`: public keys for validating work package tokens
