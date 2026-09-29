"""Tests for config_docs.py: the Markdown it renders and the README splice."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config_docs

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
    flat = config_docs.flatten_descriptions(
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
    assert config_docs.wrap_bare_urls(line) == expected


def test_wrap_bare_urls_skips_code_blocks():
    text = '```json\n"https://example.org/x"\n```\n'
    assert config_docs.wrap_bare_urls(text) == text


def test_render_parameters():
    text = config_docs.render_parameters(json.dumps(SCHEMA))
    assert text.startswith('- <a id="properties/api_url"></a>')
    assert "Where the API lives. See <https://example.org/docs>." in text
    assert '"https://example.org/api"' in text  # the example block stays verbatim
    assert "\n#### Definitions\n" in text
    assert "<br>" not in text


def test_render_readme_replaces_between_markers(tmp_path, monkeypatch):
    monkeypatch.setattr(config_docs, "format_markdown", lambda text, path: text)
    readme = tmp_path / "README.md"
    readme.write_text(
        "### Parameters\n\n"
        f"{config_docs.BEGIN_MARKER}\n\nstale\n\n{config_docs.END_MARKER}\n\n"
        "### Usage\n"
    )
    assert config_docs.render_readme(readme, "- fresh") == (
        "### Parameters\n\n"
        f"{config_docs.BEGIN_MARKER}\n\n- fresh\n\n{config_docs.END_MARKER}\n\n"
        "### Usage\n"
    )


def test_render_readme_requires_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("### Parameters\n")
    with pytest.raises(SystemExit, match="lacks the config-docs markers"):
        config_docs.render_readme(readme, "- fresh")
