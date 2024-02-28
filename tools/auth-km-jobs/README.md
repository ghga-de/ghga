
# GHGA Auth Key Management Jobs

This repo contains the script that manages JWT signing keys used by GHGA.
This script can be executed as a Kubernetes Job, either regularly or on demand.

## Keys managed by this script

The following keys are created or refreshed:

### GHGA authentication key pair

**Private** and **public** key to sign internally used authentication tokens. The service `auth-adapter` uses the private part of the key pair to sign, other GHGA microservices verify the token with the respective public part.

### External OIDC public key set

Public key set fetched from OICD provider, it is used to verify the signature of the OIDC access token included in the request.

### GHGA work package tokens

**Private** and **public** key to sign internally used work package tokens. The service `work-package` uses the private part of the key pair to sign, other GHGA microservices (for example `download-controller`) verify the token with the respective public part.

## Subcommands

The following subcommands can be executed using `run <command name>`:

- `refresh-int-keys`: Recreate internal auth token signing keys and store them in the vault
- `refresh-wps-keys`: Recreate internal work package signing keys and store them in the vault
- `refresh-ext-keys`: Refetch the external auth (OIDC) public key set and store it in the vault
- `refresh-all-keys`: Refresh all internal and external token signing keys in the vault

## Environment variables

The following environment variables are evaluated:

#### `AUTH_KM_JOBS_VAULT_ADDR`

*Optional*, default value: `http://localhost:8200`

Vault address.

#### `AUTH_KM_JOBS_VAULT_NAMESPACE`

*Optional*, default value: `vault`

Vault namespace.

#### `AUTH_KM_JOBS_TOKEN`

*Optional*, default value: `dev-token`

Vault token.

#### `AUTH_KM_JOBS_SECRET_KEY_NAME`

*Optional*, default value: `key`

Name of the key for stored secrets.

#### `AUTH_KM_JOBS_KUBE_ROLE`

*Optional*, default value: `None`

Vault Kubernetes authentication role name.

#### `AUTH_KM_JOBS_PATH_PREFIX`

*Optional*, default value: ``

Path prefix for secret paths.

#### `AUTH_KM_JOBS_PATH_INT_PRIVATE`

*Optional*, default value: `ghga-auth/private`

Internal key pair private path.

#### `AUTH_KM_JOBS_PATH_INT_PUBLIC`

*Optional*, default value: `ghga-auth/public`

Internal key pair public path.

#### `AUTH_KM_JOBS_PATH_EXT_PUBLIC`

*Optional*, default value: `oidc/public`

External OIDC key public path.

#### `AUTH_KM_JOBS_PATH_WPS_PRIVATE`

*Optional*, default value: `work-package-sign/private`

Private work-package signing key path.

#### `AUTH_KM_JOBS_PATH_WPS_PUBLIC`

*Optional*, default value: `work-package-sign/public`

Public work-package signing key path.

#### `AUTH_KM_JOBS_MOUNT_POINT`

*Optional*, default value: `secret`

Mount point for secrets engine.

#### `AUTH_KM_JOBS_VERIFY_WRITE`

*Optional*, default value: `True`

Flag to verify write.

#### `AUTH_KM_JOBS_SHOW_EXTERNAL_KEYS`

*Optional*, default value: `True`

Flag to show external keys.

#### `AUTH_KM_JOBS_SSL_VERIFY`

*Optional*, default value: `False`

SSL verification flag for Vault.

#### `AUTH_KM_JOBS_TIMEOUT`

*Optional*, default value: `30`

Timeout in seconds.

#### `AUTH_KM_JOBS_SA_TOKEN_PATH`

*Optional*, default value: `/var/run/secrets/kubernetes.io/serviceaccount/token`

Kubernetes service account token path.

#### `AUTH_KM_JOBS_OIDC_AUTHORITY_URL`

*Optional*, default value: `https://proxy.aai.lifescience-ri.eu/`

OIDC authority URL.

#### `AUTH_KM_JOBS_DISCOVERY_URL`

*Optional*, default value: `https://proxy.aai.lifescience-ri.eu/.well-known/openid-configuration`

OIDC discovery URL.
