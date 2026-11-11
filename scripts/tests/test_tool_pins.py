"""Tests that CI pins the same just and kind as the dev container, and kind's node image.

.devcontainer/post-create.sh installs both tools and is the source the others follow:
the workflows' setup-just steps, integration.yaml's kind, and the node image in
deploy/kind-config.yaml, which has to be one built for that kind release.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"


def _dev_container_version(tool: str) -> str:
    post_create = (ROOT / ".devcontainer/post-create.sh").read_text()
    [version] = re.findall(rf"^{tool}_VERSION=(\S+)$", post_create, re.M)
    return version


def test_workflows_pin_the_dev_containers_just():
    """Every setup-just step pins the just the dev container installs."""
    version = _dev_container_version("JUST")
    steps = 0
    for workflow in sorted(WORKFLOWS.glob("*.yaml")):
        text = workflow.read_text()
        uses = text.count("uses: extractions/setup-just@")
        pins = re.findall(r"just-version: (\S+)", text)
        assert len(pins) == uses, f"{workflow.name}: a setup-just step is unpinned"
        assert set(pins) <= {version}, f"{workflow.name} pins {pins}, not {version}"
        steps += uses
    assert steps > 0


def test_integration_gate_pins_the_dev_containers_kind():
    """The test bed runs on the same kind in CI as locally."""
    text = (WORKFLOWS / "integration.yaml").read_text()
    [pinned] = re.findall(
        r"uses: helm/kind-action@\S+\n(?:\s+.*\n)*?\s+version: (\S+)", text
    )
    assert pinned == f"v{_dev_container_version('KIND')}"


def test_node_image_is_digest_pinned_for_that_kind():
    """A node image only works with the kind release it was built for, so a kind bump
    must move the image too; the comment above it names the release."""
    config = (ROOT / "deploy/kind-config.yaml").read_text()
    [image] = re.findall(r"^\s+image: (\S+)$", config, re.M)
    assert re.fullmatch(r"kindest/node:v[\d.]+@sha256:[0-9a-f]{64}", image)
    assert f"built for kind v{_dev_container_version('KIND')}" in config
