import json
from pathlib import Path
import subprocess
from typing import Any
import hashlib

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CASES_DIR = Path(__file__).resolve().parent / "cases"
DUMMY_CHART_DIR = BASE_DIR / "base" / "tests" / "dummy"
RENDER_TO_FILES = True


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}, got {type(data).__name__}")
    return data


def _deep_merge(base: Any, override: Any) -> Any:
    # Compose values files in a Helm-friendly way: maps merge, everything else replaces.
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, value in override.items():
            result[key] = _deep_merge(result[key], value) if key in result else value
        return result
    return override


@pytest.fixture(scope="session")
def _dependency_update():
    o = subprocess.run(
        ["helm", "dep", "up", str(DUMMY_CHART_DIR), "--skip-refresh"],
        capture_output=True,
        text=True,
    )

    if o.returncode != 0:
        raise AssertionError(
            f"Helm dependency update failed: {' '.join(o.args)}\nstdout:\n{o.stdout}\nstderr:\n{o.stderr}"
        )


@pytest.fixture()
def release_name():
    return "test"


def _render_chart_case(composed_values: dict[str, Any], release_name: str) -> str:
    output = subprocess.run(
        [
            "helm",
            "template",
            release_name,
            "--namespace",
            "test",
            "--values",
            "-",
            str(DUMMY_CHART_DIR),
        ],
        capture_output=True,
        text=True,
        input=yaml.dump(composed_values),
    )
    if RENDER_TO_FILES:
        sha = hashlib.sha256(
            json.dumps(composed_values, sort_keys=True).encode()
        ).hexdigest()
        subprocess.run(
            [
                "helm",
                "template",
                release_name,
                "--output-dir",
                f"./rendered/{sha[:8]}/",
                "--namespace",
                "test",
                "--values",
                "-",
                str(DUMMY_CHART_DIR),
            ],
            capture_output=True,
            text=True,
            input=yaml.dump(composed_values),
        )

    if output.returncode != 0:
        raise AssertionError(
            f"Helm command failed: {' '.join(output.args)}\nstdout:\n{output.stdout}\nstderr:\n{output.stderr}"
        )
    return output.stdout


def _load_objects_from_yaml(yaml_str: str) -> dict[str, Any]:
    objects = yaml.safe_load_all(yaml_str)
    objects_dict = {}
    for obj in objects:
        if obj.get("kind") in objects_dict:
            raise ValueError(
                f"Duplicate object kind '{obj.get('kind')}' found in rendered manifests. All objects must have unique 'kind' fields."
            )
        else:
            objects_dict[obj.get("kind")] = obj
    return objects_dict


def compose_values(*filenames: str) -> dict[str, Any]:
    composed: dict[str, Any] = {}
    for name in filenames:
        composed = _deep_merge(composed, _load_yaml(CASES_DIR / "values" / name))
    return composed


@pytest.fixture
def rendered_chart(_dependency_update, release_name):
    def _factory(*filenames: str):
        composed_values = compose_values(*filenames)
        return _load_objects_from_yaml(
            _render_chart_case(composed_values, release_name)
        )

    return _factory


@pytest.fixture
def expected():
    def _factory(case: str, key: str):
        expected = _load_yaml(CASES_DIR / "expected" / f"{case}.yaml")
        return expected[key]

    return _factory
