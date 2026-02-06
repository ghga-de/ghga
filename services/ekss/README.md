# Encryption Key Store Service

providing crypt4gh file secret extraction, storage and envelope generation

## Description

This service implements an interface to extract file encryption secrects from a
[GA4GH Crypt4GH](https://www.ga4gh.org/news/crypt4gh-a-secure-method-for-sharing-human-genetic-data/)
encrypted file into a HashiCorp Vault and produce user-specific file envelopes
containing these secrets.


### API endpoints:

#### `POST /secrets`:

This endpoint takes in the first part of a crypt4gh encrypted file that contains the
file envelope and a client public key.
It decrypts the envelope, using the clients public and GHGA's private key to obtain
the original encryption secret.
Subsequently, a new random secret that can be used for re-encryption and is created
and stored in the vault.
The original secret is *not* saved in the vault.

This endpoint returns the extracted secret, the newly generated secret, the envelope offset
(length of the envelope) and the secret id which can be used to retrieve the new secret from the vault.


#### `GET /secrets/{secret_id}/envelopes/{client_pk}`:

This endpoint takes a secret_id and a client public key.
It retrieves the corresponding secret from the vault and encrypts it with GHGAs
private key and the clients public key to create a crypt4gh file envelope.

This enpoint returns the envelope.


#### `DELETE /secrets/{secret_id}`:

This endpoint takes a secret_id.
It deletes the corresponding secret from the Vault.
This enpoint returns a 204 Response, if the deletion was successfull
or a 404 response, if the secret_id did not exist.

### Vault configuration:

For the aforementioned endpoints to work correctly, the vault instance the encryption
key store communicates with needs to set policies granting *create* and *read* privileges
on all secret paths managed and *delete* priviliges on the respective metadata.

For all encryption keys stored under a prefix of *ekss* this might look like
```
path "secret/data/ekss/*" {
    capabilities = ["read", "create"]
}
path "secret/metadata/ekss/*" {
    capabilities = ["delete"]
}
```


## Installation

We recommend using the provided Docker container.

A pre-built version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/encryption-key-store-service):
```bash
docker pull ghga/encryption-key-store-service:4.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/encryption-key-store-service:4.1.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/encryption-key-store-service:4.1.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
ekss --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- <a id="properties/enable_opentelemetry"></a>**`enable_opentelemetry`** *(boolean)*: If set to true, this will run necessary setup code.If set to false, environment variables are set that should also effectively disable autoinstrumentation. Default: `false`.

- <a id="properties/otel_trace_sampling_rate"></a>**`otel_trace_sampling_rate`** *(number)*: Determines which proportion of spans should be sampled. A value of 1.0 means all and is equivalent to the previous behaviour. Setting this to 0 will result in no spans being sampled, but this does not automatically set `enable_opentelemetry` to False. Minimum: `0`. Maximum: `1`. Default: `1.0`.

- <a id="properties/server_private_key_path"></a>**`server_private_key_path`** *(string, format: path, required)*: Path to the Crypt4GH private key file.


  Examples:

  ```json
  "./key.sec"
  ```


- <a id="properties/server_public_key_path"></a>**`server_public_key_path`** *(string, format: path, required)*: Path to the Crypt4GH public key file.


  Examples:

  ```json
  "./key.pub"
  ```


- <a id="properties/private_key_passphrase"></a>**`private_key_passphrase`**: Passphrase needed to read the content of the private key file. Only needed if the private key is encrypted. Default: `null`.

  - **Any of**

    - <a id="properties/private_key_passphrase/anyOf/0"></a>*string*

    - <a id="properties/private_key_passphrase/anyOf/1"></a>*null*

- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture. Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE". Default: `"INFO"`.

- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"ekss"`.

- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service. This is included in log messages.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


- <a id="properties/log_format"></a>**`log_format`**: If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details. Default: `null`.

  - **Any of**

    - <a id="properties/log_format/anyOf/0"></a>*string*

    - <a id="properties/log_format/anyOf/1"></a>*null*


  Examples:

  ```json
  "%(timestamp)s - %(service)s - %(level)s - %(message)s"
  ```


  ```json
  "%(asctime)s - Severity: %(levelno)s - %(msg)s"
  ```


- <a id="properties/log_traceback"></a>**`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages. Default: `true`.

- <a id="properties/vault_url"></a>**`vault_url`** *(string, required)*: URL of the vault instance to connect to.


  Examples:

  ```json
  "http://127.0.0.1.8200"
  ```


- <a id="properties/vault_role_id"></a>**`vault_role_id`**: Vault role ID to access a specific prefix. Default: `null`.

  - **Any of**

    - <a id="properties/vault_role_id/anyOf/0"></a>*string, format: password*

    - <a id="properties/vault_role_id/anyOf/1"></a>*null*


  Examples:

  ```json
  "example_role"
  ```


- <a id="properties/vault_secret_id"></a>**`vault_secret_id`**: Vault secret ID to access a specific prefix. Default: `null`.

  - **Any of**

    - <a id="properties/vault_secret_id/anyOf/0"></a>*string, format: password*

    - <a id="properties/vault_secret_id/anyOf/1"></a>*null*


  Examples:

  ```json
  "example_secret"
  ```


- <a id="properties/vault_verify"></a>**`vault_verify`**: SSL certificates (CA bundle) used to verify the identity of the vault, or True to use the default CAs, or False for no verification. Default: `true`.

  - **Any of**

    - <a id="properties/vault_verify/anyOf/0"></a>*boolean*

    - <a id="properties/vault_verify/anyOf/1"></a>*string*


  Examples:

  ```json
  "/etc/ssl/certs/my_bundle.pem"
  ```


- <a id="properties/vault_path"></a>**`vault_path`** *(string, required)*: Path without leading or trailing slashes where secrets should be stored in the vault.

- <a id="properties/vault_secrets_mount_point"></a>**`vault_secrets_mount_point`** *(string)*: Name used to address the secret engine under a custom mount path. Default: `"secret"`.


  Examples:

  ```json
  "secret"
  ```


- <a id="properties/vault_kube_role"></a>**`vault_kube_role`**: Vault role name used for Kubernetes authentication. Default: `null`.

  - **Any of**

    - <a id="properties/vault_kube_role/anyOf/0"></a>*string*

    - <a id="properties/vault_kube_role/anyOf/1"></a>*null*


  Examples:

  ```json
  "file-ingest-role"
  ```


- <a id="properties/vault_auth_mount_point"></a>**`vault_auth_mount_point`**: Adapter specific mount path for the corresponding auth backend. If none is provided, the default is used. Default: `null`.

  - **Any of**

    - <a id="properties/vault_auth_mount_point/anyOf/0"></a>*string*

    - <a id="properties/vault_auth_mount_point/anyOf/1"></a>*null*


  Examples:

  ```json
  null
  ```


  ```json
  "approle"
  ```


  ```json
  "kubernetes"
  ```


- <a id="properties/service_account_token_path"></a>**`service_account_token_path`** *(string, format: path)*: Path to service account token used by kube auth adapter. Default: `"/var/run/secrets/kubernetes.io/serviceaccount/token"`.

- <a id="properties/host"></a>**`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.

- <a id="properties/port"></a>**`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- <a id="properties/auto_reload"></a>**`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.

- <a id="properties/workers"></a>**`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- <a id="properties/timeout_keep_alive"></a>**`timeout_keep_alive`** *(integer)*: The time in seconds to keep an idle connection open for subsequent requests before closing it. This value should be higher than the timeout used by any client or reverse proxy to avoid premature connection closures. Default: `90`.


  Examples:

  ```json
  5
  ```


  ```json
  90
  ```


  ```json
  5400
  ```


- <a id="properties/api_root_path"></a>**`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `""`.

- <a id="properties/openapi_url"></a>**`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `"/openapi.json"`.

- <a id="properties/docs_url"></a>**`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `"/docs"`.

- <a id="properties/cors_allowed_origins"></a>**`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_origins/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_origins/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_origins/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allow_credentials"></a>**`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allow_credentials/anyOf/0"></a>*boolean*

    - <a id="properties/cors_allow_credentials/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- <a id="properties/cors_allowed_methods"></a>**`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_methods/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_methods/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_methods/anyOf/1"></a>*null*


  Examples:

  ```json
  [
      "*"
  ]
  ```


- <a id="properties/cors_allowed_headers"></a>**`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all request headers. The Accept, Accept-Language, Content-Language, Content-Type and some are always allowed for CORS requests. Default: `null`.

  - **Any of**

    - <a id="properties/cors_allowed_headers/anyOf/0"></a>*array*

      - <a id="properties/cors_allowed_headers/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_allowed_headers/anyOf/1"></a>*null*


  Examples:

  ```json
  []
  ```


- <a id="properties/cors_exposed_headers"></a>**`cors_exposed_headers`**: A list of HTTP response headers that should be exposed for cross-origin responses. Defaults to []. Note that you can NOT use ['*'] to expose all response headers. The Cache-Control, Content-Language, Content-Length, Content-Type, Expires, Last-Modified and Pragma headers are always exposed for CORS responses. Default: `null`.

  - **Any of**

    - <a id="properties/cors_exposed_headers/anyOf/0"></a>*array*

      - <a id="properties/cors_exposed_headers/anyOf/0/items"></a>**Items** *(string)*

    - <a id="properties/cors_exposed_headers/anyOf/1"></a>*null*


  Examples:

  ```json
  []
  ```


- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```



### Usage:

A template YAML for configuring the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.ekss.yaml`, and place it in one of the following locations:
- in the current working directory where you execute the service (on Linux: `./.ekss.yaml`)
- in your home directory (on Linux: `~/.ekss.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `ekss_`,
e.g. for the `host` set an environment variable named `ekss_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To use file secrets, please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](openapi.yaml).

## Architecture and Design:
This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.


## Development

For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of VS Code
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as VS Code with its "Remote - Containers"
extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in VS Code and run the command
`Remote-Containers: Reopen in Container` from the VS Code "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant VS Code extensions pre-installed
- pre-configured linting and auto-formatting
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, a command `dev_install` is available for convenience.
It installs the service with all development dependencies, and it installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`./requirements-dev.txt`](./requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [`readme_generation.md`](./readme_generation.md)
for details.
