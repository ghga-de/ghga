"""Vault-backed integration tests for refresh key CLI commands."""

import http.server
import importlib
import json
import os
import threading
from typing import Generator

import pytest
from typer.testing import CliRunner

from auth_km_jobs.config import Config
from auth_km_jobs.vault import get_vault

runner = CliRunner()
config = Config()


@pytest.fixture()
def vault_client() -> Generator:
    """Return a Vault client for tests."""
    client = get_vault()

    def delete(path: str):
        path = config.path_prefix + path
        client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path, mount_point=config.mount_point
        )

    paths = [
        config.path_int_private,
        config.path_int_public,
        config.path_wps_private,
        config.path_wps_public,
        config.path_ext_public,
    ]

    for p in paths:
        delete(p)

    yield client

    # cleanup after test
    for p in paths:
        delete(p)


class _SimpleHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self):
        host, port = self.server.server_address  # type: ignore[attr-defined]
        base_url = f"http://{host}:{port}"
        if self.path == "/discovery":
            self._send_json(
                {
                    "issuer": f"{base_url}/",
                    "jwks_uri": f"{base_url}/jwks",
                }
            )
            return
        if self.path == "/jwks":
            self._send_json({"keys": [{"kty": "oct", "k": "fakekey"}]})
            return
        self._send_json({"error": "not found"}, code=404)


def _start_test_http_server() -> tuple[http.server.HTTPServer, threading.Thread]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _SimpleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _reload_cli_with_env(**env):
    """Set env vars and reload CLI/jwks modules so they pick them up."""
    os.environ.update({k: str(v) for k, v in env.items()})
    import auth_km_jobs.jwks as jwks_mod

    importlib.reload(jwks_mod)
    import auth_km_jobs.__main__ as cli_mod

    importlib.reload(cli_mod)
    return cli_mod


def _read_secret_from_vault(client, path: str) -> str:
    resp = client.secrets.kv.read_secret_version(
        path=path, mount_point=config.mount_point, raise_on_deleted_version=True
    )
    return resp["data"]["data"][config.secret_key_name]


def test_refresh_int_keys_vault_integration(vault_client):
    cfg = Config()
    import auth_km_jobs.__main__ as cli_mod

    result = runner.invoke(cli_mod.app, ["refresh-int-keys"])
    assert result.exit_code == 0, result.output

    priv_json = _read_secret_from_vault(
        vault_client, cfg.path_prefix + cfg.path_int_private
    )
    pub_json = _read_secret_from_vault(
        vault_client, cfg.path_prefix + cfg.path_int_public
    )

    priv = json.loads(priv_json)
    pub = json.loads(pub_json)
    assert isinstance(priv, dict) and isinstance(pub, dict)
    assert priv.get("kty") == "EC" and pub.get("kty") == "EC"
    assert priv != pub


def test_refresh_wps_keys_vault_integration(vault_client):
    cfg = Config()
    import auth_km_jobs.__main__ as cli_mod

    result = runner.invoke(cli_mod.app, ["refresh-wps-keys"])  # hyphenated command
    assert result.exit_code == 0, result.output

    priv_json = _read_secret_from_vault(
        vault_client, cfg.path_prefix + cfg.path_wps_private
    )
    pub_json = _read_secret_from_vault(
        vault_client, cfg.path_prefix + cfg.path_wps_public
    )

    priv = json.loads(priv_json)
    pub = json.loads(pub_json)
    assert isinstance(priv, dict) and isinstance(pub, dict)
    assert priv.get("kty") == "EC" and pub.get("kty") == "EC"
    assert priv != pub


def test_refresh_ext_keys_vault_integration(vault_client):
    server, thread = _start_test_http_server()
    host, port = server.server_address  # type: ignore[attr-defined]
    base_url = f"http://{host}:{port}"
    try:
        authority = f"{base_url}/"
        discovery_url = f"{base_url}/discovery"
        cli_mod = _reload_cli_with_env(
            AUTH_KM_JOBS_DISCOVERY_URL=discovery_url,
            AUTH_KM_JOBS_OIDC_AUTHORITY_URL=authority,
        )

        result = runner.invoke(cli_mod.app, ["refresh-ext-keys"])
        assert result.exit_code == 0, result.output

        jwks_text = _read_secret_from_vault(
            vault_client, config.path_prefix + config.path_ext_public
        )
        jwks = json.loads(jwks_text)
        assert isinstance(jwks, dict)
        assert (
            "keys" in jwks and isinstance(jwks["keys"], list) and len(jwks["keys"]) == 1
        )
    finally:
        server.shutdown()
        thread.join(timeout=1)
