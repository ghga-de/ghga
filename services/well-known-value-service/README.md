# Well Known Value Service

Well-Known-Value-Service - Provides access to common values via API

## Description

This service is intended to provide access to configured values via API in order to reduce the required config for other GHGA microservices.

## Installation

Each GHGA platform release publishes the service as a container image on [Docker Hub](https://hub.docker.com/r/ghga/wkvs), tagged with the platform version:

```bash
docker pull ghga/wkvs:<platform-version>
```

To build the image yourself, run this from the repository root:

```bash
docker build -f docker/Dockerfile --build-arg PACKAGE=wkvs --build-arg EXECUTABLE=wkvs -t ghga/wkvs .
```

The entrypoint starts the service, which reads its settings as described under [Configuration](#configuration):

```bash
docker run -p 8080:8080 ghga/wkvs:<platform-version>
```

For Kubernetes, use the Helm chart [`wkvs`](../../deploy/charts/wkvs/README.md):

```bash
helm install wkvs oci://registry-1.docker.io/ghga/wkvs-chart
```

To run the service without a container, start it from the repository root in the workspace environment:

```bash
uv run wkvs
```

## Configuration

### Parameters

The service requires the following configuration parameters:

- <a id="properties/log_level"></a>**`log_level`** *(string)*: The minimum log level to capture.
  Must be one of: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "TRACE".
  Default: `"INFO"`.
- <a id="properties/service_name"></a>**`service_name`** *(string)*: Default: `"wkvs"`.
- <a id="properties/service_instance_id"></a>**`service_instance_id`** *(string, required)*: A string that uniquely identifies this instance across all instances of this service.
  This is included in log messages.

  Examples:

  ```json
  "germany-bw-instance-001"
  ```

- <a id="properties/log_format"></a>**`log_format`**: If set, will replace JSON formatting with the specified string format.
  If not set, has no effect.
  In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details.
  Default: `null`.
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

- <a id="properties/log_traceback"></a>**`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages.
  Default: `true`.
- <a id="properties/dcs_api_url"></a>**`dcs_api_url`** *(string, required)*: URL to the root of the DRS-compatible DCS API.
- <a id="properties/ucs_api_url"></a>**`ucs_api_url`** *(string, required)*: URL to the root of the upload controller API.
- <a id="properties/wps_api_url"></a>**`wps_api_url`** *(string, required)*: URL to the root of the WPS API.
- <a id="properties/storage_aliases"></a>**`storage_aliases`** *(object, required)*: Mapping of storage alias to endpoint URL for all available S3 object storages.
  Can contain additional properties.
  - <a id="properties/storage_aliases/additionalProperties"></a>**Additional properties** *(string, format: uri)*: Length must be between 1 and 2083 (inclusive).
- <a id="properties/storage_labels"></a>**`storage_labels`** *(object, required)*: Mapping of storage alias to its human-readable format.
  Can contain additional properties.
  - <a id="properties/storage_labels/additionalProperties"></a>**Additional properties** *(string)*

  Examples:

  ```json
  {
      "HD01": "Heidelberg",
      "TUE01": "T\u00fcbingen"
  }
  ```

- <a id="properties/crypt4gh_public_keys"></a>**`crypt4gh_public_keys`** *(object, required)*: Mapping of storage alias to Crypt4GH public key.
  Can contain additional properties.
  - <a id="properties/crypt4gh_public_keys/additionalProperties"></a>**Additional properties** *(string)*
- <a id="properties/host"></a>**`host`** *(string)*: IP of the host.
  Default: `"127.0.0.1"`.
- <a id="properties/port"></a>**`port`** *(integer)*: Port to expose the server on the specified host.
  Default: `8080`.
- <a id="properties/auto_reload"></a>**`auto_reload`** *(boolean)*: A development feature.
  Set to `True` to automatically reload the server upon code changes.
  Default: `false`.
- <a id="properties/workers"></a>**`workers`** *(integer)*: Number of workers processes to run.
  Default: `1`.
- <a id="properties/timeout_keep_alive"></a>**`timeout_keep_alive`** *(integer)*: The time in seconds to keep an idle connection open for subsequent requests before closing it.
  This value should be higher than the timeout used by any client or reverse proxy to avoid premature connection closures.
  Default: `90`.

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

- <a id="properties/api_root_path"></a>**`api_root_path`** *(string)*: Root path at which the API is reachable.
  This is relative to the specified host and port.
  Default: `""`.
- <a id="properties/openapi_url"></a>**`openapi_url`** *(string)*: Path to get the openapi specification in JSON format.
  This is relative to the specified host and port.
  Default: `"/openapi.json"`.
- <a id="properties/docs_url"></a>**`docs_url`** *(string)*: Path to host the swagger documentation.
  This is relative to the specified host and port.
  Default: `"/docs"`.
- <a id="properties/cors_allowed_origins"></a>**`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests.
  By default, cross-origin requests are not allowed.
  You can use ['*'] to allow any origin.
  Default: `null`.
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

- <a id="properties/cors_allow_credentials"></a>**`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests.
  Defaults to False.
  Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed.
  The origins must be explicitly specified.
  Default: `null`.
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

- <a id="properties/cors_allowed_methods"></a>**`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests.
  Defaults to ['GET'].
  You can use ['*'] to allow all standard methods.
  Default: `null`.
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

- <a id="properties/cors_allowed_headers"></a>**`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests.
  Defaults to [].
  You can use ['*'] to allow all request headers.
  The Accept, Accept-Language, Content-Language, Content-Type and some are always allowed for CORS requests.
  Default: `null`.
  - **Any of**
    - <a id="properties/cors_allowed_headers/anyOf/0"></a>*array*
      - <a id="properties/cors_allowed_headers/anyOf/0/items"></a>**Items** *(string)*
    - <a id="properties/cors_allowed_headers/anyOf/1"></a>*null*

  Examples:

  ```json
  []
  ```

- <a id="properties/cors_exposed_headers"></a>**`cors_exposed_headers`**: A list of HTTP response headers that should be exposed for cross-origin responses.
  Defaults to [].
  Note that you can NOT use ['*'] to expose all response headers.
  The Cache-Control, Content-Language, Content-Length, Content-Type, Expires, Last-Modified and Pragma headers are always exposed for CORS responses.
  Default: `null`.
  - **Any of**
    - <a id="properties/cors_exposed_headers/anyOf/0"></a>*array*
      - <a id="properties/cors_exposed_headers/anyOf/0/items"></a>**Items** *(string)*
    - <a id="properties/cors_exposed_headers/anyOf/1"></a>*null*

  Examples:

  ```json
  []
  ```

- <a id="properties/generate_correlation_id"></a>**`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID.
  If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function.
  Default: `true`.

  Examples:

  ```json
  true
  ```

  ```json
  false
  ```

### Usage

A template YAML file for configuring the service can be found at [`./example_config.yaml`](./example_config.yaml).
Please adapt it, rename it to `.wkvs.yaml`, and place it in one of the following locations:

- in the current working directory where you execute the service (on Linux: `./.wkvs.yaml`)
- in your home directory (on Linux: `~/.wkvs.yaml`)

The config YAML file will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example_config.yaml`](./example_config.yaml) can also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `wkvs_`, e.g. for the `host` set an environment variable named `wkvs_host` (you may use both upper or lower cases, however, it is standard to define all env variables in upper cases).

To use file secrets, please refer to the [corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support) of the pydantic documentation.

## HTTP API

The service's OpenAPI specification is in [`openapi.yaml`](./openapi.yaml).

## Architecture and Design

The Well-Known-Value-Service does not currently utilize the ports or core portions of the triple hexagonal architecture, but it does retain the adapters portion of the design in case the service is extended later.

## Development

The service is a member of the [GHGA monorepo](../../README.md), which provides the development environment: work in its dev container, as described in [Work inside the dev container](../../README.md#work-inside-the-dev-container).
Run the service's tests with `just test services/well-known-value-service`, and the linters with `just lint`.

## License

This repository is free to use and modify according to the [Apache 2.0 License](./LICENSE).
