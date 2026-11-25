"""Tests for service_docs.py: member selection, the Markdown, the README splice and
the secret typing check."""

import json
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, Secret, SecretStr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import service_docs

SCHEMA = {
    "properties": {
        "api_url": {
            "default": "https://example.org/api",
            "description": "Where the API lives.\n\nSee https://example.org/docs.",
            "examples": ["https://example.org/api"],
            "type": "string",
        },
        "nested": {"$ref": "#/$defs/Nested"},
    },
    "$defs": {
        "Nested": {
            "description": "A nested model.",
            "properties": {"flag": {"default": False, "type": "boolean"}},
            "type": "object",
        }
    },
    "type": "object",
}


def test_flatten_descriptions_joins_lines_everywhere():
    flat = service_docs.flatten_descriptions(
        {"description": "a\n  b\n\nc", "items": [{"description": "d\ne"}]}
    )
    assert flat == {"description": "a b c", "items": [{"description": "d e"}]}


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("See https://example.org/x.", "See <https://example.org/x>."),
        ("Already <https://example.org/x>.", "Already <https://example.org/x>."),
        ("A [link](https://example.org/x).", "A [link](https://example.org/x)."),
        ('Default: `"https://example.org/x"`.', 'Default: `"https://example.org/x"`.'),
        ("Should start with https://.", "Should start with https://."),
    ],
)
def test_wrap_bare_urls(line, expected):
    assert service_docs.wrap_bare_urls(line) == expected


def test_wrap_bare_urls_skips_code_blocks():
    text = '```json\n"https://example.org/x"\n```\n'
    assert service_docs.wrap_bare_urls(text) == text


def test_render_parameters():
    text = service_docs.render_parameters(json.dumps(SCHEMA))
    assert text.startswith('- <a id="properties/api_url"></a>')
    assert "Where the API lives. See <https://example.org/docs>." in text
    assert '"https://example.org/api"' in text  # the example block stays verbatim
    assert "\n#### Definitions\n" in text
    assert "<br>" not in text


def test_render_readme_replaces_between_markers(tmp_path, monkeypatch):
    monkeypatch.setattr(service_docs, "format_markdown", lambda text, path: text)
    readme = tmp_path / "README.md"
    readme.write_text(
        "### Parameters\n\n"
        f"{service_docs.BEGIN_MARKER}\n\nstale\n\n{service_docs.END_MARKER}\n\n"
        "## HTTP API\n"
    )
    assert service_docs.render_readme(readme, "- fresh") == (
        "### Parameters\n\n"
        f"{service_docs.BEGIN_MARKER}\n\n- fresh\n\n{service_docs.END_MARKER}\n\n"
        "## HTTP API\n"
    )


def test_render_readme_requires_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("### Parameters\n")
    with pytest.raises(SystemExit, match="lacks the config-docs markers"):
        service_docs.render_readme(readme, "- fresh")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A workspace with two services that carry a config schema and one that does not."""
    for member in ("services/a", "services/b", "services/c"):
        (tmp_path / member).mkdir(parents=True)
    for member in ("services/a", "services/b"):
        (tmp_path / member / service_docs.SCHEMA_FILE).write_text("{}")
    monkeypatch.setattr(service_docs, "ROOT", tmp_path)
    return tmp_path


def test_members_default_to_all(workspace):
    assert service_docs.members([]) == [
        workspace / "services/a",
        workspace / "services/b",
    ]


def test_members_of_the_paths(workspace):
    paths = ["services/b/src/b/config.py", "services/c/README.md"]
    assert service_docs.members(paths) == [workspace / "services/b"]


def test_members_all_for_a_path_outside_members(workspace):
    paths = ["services/b/README.md", "scripts/service_docs.py"]
    assert service_docs.members(paths) == [
        workspace / "services/a",
        workspace / "services/b",
    ]


class Nested(BaseModel):
    """A nested model with a secret typed as a plain string."""

    password: str
    region: str


class PlannedConfig(BaseModel):
    """A config with secrets typed right, wrong, and fields that only look secret."""

    db_password: SecretStr
    api_token_secret: Secret[str]
    key_passphrase: str | None = None
    signing_key: str
    private_key_path: str
    vault_secret_id: str
    vault_secrets_mount_point: str
    mongo_dsn: str
    s3_session_token: str
    token_hashes: list[str]
    cors_allow_credentials: bool
    auth_key: str
    nested: Nested


def test_unmasked_secrets():
    found = list(service_docs.unmasked_secrets(PlannedConfig, {"auth_key"}))
    assert sorted(found) == [
        "auth_key",
        "key_passphrase",
        "mongo_dsn",
        "nested.password",
        "s3_session_token",
        "signing_key",
        "vault_secret_id",
    ]
