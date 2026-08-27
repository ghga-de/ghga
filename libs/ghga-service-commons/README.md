[![PyPI version shields.io](https://img.shields.io/pypi/v/ghga-service-commons.svg)](https://pypi.org/project/ghga-service-commons/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ghga-service-commons.svg)](https://pypi.org/project/ghga-service-commons/)

# ghga-service-commons
This Python library serves as a collection of common utilities used by
the microservices developed at German Human Genome-Phenome Archive (GHGA).

It collects boilerplate code for common functionalities such as API server setup,
authentication and authorization.

This library is primarily intended for internal use at GHGA and should
not be seen as a general-purpose microservice chassis.
However, if this library matches your specific needs as well,
please feel free to use it. It is open source.

# Installation
This package is available at PyPI:
https://pypi.org/project/ghga_service_commons

You can install it from there using:
```
pip install ghga_service_commons
```

Thereby, you may specify following extra(s):
- `api`: dependencies needed to use the API server functionalities
- `auth`: dependencies needed for dealing with authentication and authorization

# Mocking the APIs a service calls
Outbound HTTP calls are tested against a mock of the API they go to, rather than
against the network. `ghga_service_commons.api.mock_router` routes requests to the
endpoints registered on it, and `ghga_service_commons.api.mock_api` builds the mocks
themselves on top of it.

Model an API once, declaring each endpoint and how it answers when a test says nothing
about it:
```python
from ghga_service_commons.api.mock_api import ApiMock, endpoint, respond


class EkssApiMock(ApiMock):
    """A mock of the EKSS API endpoints that this service talks to."""

    on_get_envelope = endpoint(
        "GET", "/secrets/{secret_id}/envelopes", respond(200, json={"content": "..."})
    )
    on_delete_secret = endpoint("DELETE", "/secrets/{secret_id}", respond(204))
```
A test then states only what it cares about, and mounts the mock on the client under
test:
```python
ekss = EkssApiMock(base_url=str(config.ekss_api_url))
ekss.on_delete_secret = respond(500)

async with httpx2.AsyncClient(transport=ekss.as_transport()) as client:
    ...

assert str(ekss.last_request.url).endswith("/secrets/some-id")
```
An endpoint declared without a default refuses to make up a response, so a test never
gets one by accident. Besides `respond`, the module has `fail_to_connect`, `fail_with`
and `in_sequence`; anything else taking the request, plus the endpoint's path variables
as keyword arguments, works as a handler too, `async` ones included.

The transport returned by `as_transport()` answers every request, so a test using it
cannot reach the network. Where one client talks to several APIs, or also has to carry
real traffic, mount a `RoutingTransport` over the mocks instead. Code that builds its
own client, and hence takes no transport, is redirected with `patch_httpx_module`.

## Development

This package is a member of the [GHGA monorepo](https://github.com/ghga-de/ghga) and is
developed from the repository root rather than on its own. The repository ships a
devcontainer with the whole toolchain: open it in VS Code and run
`Remote-Containers: Reopen in Container`, or set the environment up directly with
`just sync`.

The usual tasks, run from the repository root (see
[ADR-0015](https://github.com/ghga-de/ghga/blob/main/docs/adr/0015-task-runner.md) for the
full recipe list):

```bash
just sync                            # install every member plus the shared dev toolchain
just test libs/ghga-service-commons  # this member's test suite
just lint                            # ruff check + format check across the workspace
```

## License
This repository is free to use and modify according to the [Apache 2.0 License](https://github.com/ghga-de/ghga/blob/main/libs/ghga-service-commons/LICENSE).
