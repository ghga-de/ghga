"""Unit tests for the image reference the chart generator derives per member."""

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import create_charts
from create_charts import MONO_IMAGE, derived_values, image_name

PYTHON_MEMBER = {"package": "wps", "kind": "python"}
FRONTEND_MEMBER = {"package": "data-portal", "kind": "frontend"}


@pytest.mark.parametrize(
    "member, mono, expected",
    [
        (PYTHON_MEMBER, False, "wps"),
        (PYTHON_MEMBER, True, MONO_IMAGE),
        (FRONTEND_MEMBER, False, "data-portal"),
        (FRONTEND_MEMBER, True, "data-portal"),
    ],
)
def test_image_name(member, mono, expected):
    """Only Python members move to the mono image; the front end keeps its own."""
    assert image_name(member, mono) == expected


def test_mono_keeps_the_member_executable():
    """The mono image starts each service by its own console script."""
    values = derived_values(PYTHON_MEMBER, "ghcr.io/ghga-de/ghga", mono=True)
    assert values["image"] == {
        "registry": "ghcr.io",
        "repository": f"ghga-de/ghga/{MONO_IMAGE}",
    }
    assert values["executable"] == "wps"


def _dev_run(tmp_path, monkeypatch, digests: dict) -> None:
    """Generate the charts into tmp_path the way dev-images.yaml does."""
    demo = tmp_path / "ghga-demo"
    demo.mkdir()
    for name in ("Chart.yaml", "values.yaml"):
        shutil.copy(create_charts.DEMO_CHART / name, demo / name)
    digests_file = tmp_path / "digests.json"
    digests_file.write_text(json.dumps(digests))
    monkeypatch.setattr(create_charts, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(create_charts, "DEMO_CHART", demo)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("create_charts.py", "--version", "0.0.0-dev.101", "--mono"),
            *("--chart-registry", "ghcr.io/ghga-de/ghga/charts", "--chart-suffix", ""),
            *("--digests", str(digests_file), "--require-digests"),
        ],
    )
    create_charts.main()


def test_mono_run_pins_the_mono_digest(tmp_path, monkeypatch):
    """A --mono run pins Python members to the mono digest, the front end to its own."""
    _dev_run(
        tmp_path,
        monkeypatch,
        {MONO_IMAGE: "sha256:mono", "data-portal": "sha256:portal"},
    )

    def image(chart: str) -> dict:
        return yaml.safe_load((tmp_path / chart / "values.yaml").read_text())["image"]

    assert image("wps")["digest"] == "sha256:mono"
    assert image("data-portal")["digest"] == "sha256:portal"
    readme = (tmp_path / "wps" / "README.md").read_text()
    assert "oci://ghcr.io/ghga-de/ghga/charts/wps\n" in readme


def test_require_digests_fails_on_a_missing_one(tmp_path, monkeypatch):
    """A member whose image was not built stops the run instead of getting a tag."""
    with pytest.raises(SystemExit, match="no digest for data-portal"):
        _dev_run(tmp_path, monkeypatch, {MONO_IMAGE: "sha256:mono"})
