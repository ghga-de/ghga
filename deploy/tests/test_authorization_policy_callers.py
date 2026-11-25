"""Check the AuthorizationPolicy callers against the callee's API and the known charts.

No schema sees a path the API does not have, or a route renamed under a policy; in
production those surface as 403s. Here they fail CI instead.
"""

import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
CHARTS = REPO / "deploy" / "charts"
sys.path.insert(0, str(REPO / "scripts"))
from image_members import image_members

MEMBER_PATHS = {m["package"]: REPO / m["path"] for m in image_members()}
UMBRELLA_DEPENDENCIES = yaml.safe_load(
    (CHARTS / "ghga-demo" / "Chart.yaml").read_text()
)["dependencies"]
UMBRELLA_INSTANCES = {
    dep.get("alias", dep["name"]): dep["name"]
    for dep in UMBRELLA_DEPENDENCIES
    if dep["name"] in MEMBER_PATHS
}
KNOWN_CALLERS = set(MEMBER_PATHS) | set(UMBRELLA_INSTANCES)


def _callers(values: dict[str, Any]) -> dict[str, Any]:
    return (values.get("authorizationPolicy") or {}).get("callers") or {}


def _policies() -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    """(source, callee chart, caller, operations) for every caller in the repo."""
    found = []
    for chart in sorted(MEMBER_PATHS):
        values_file = CHARTS / chart / "values.yaml"
        if values_file.is_file():
            values = yaml.safe_load(values_file.read_text())
            for caller, operations in _callers(values).items():
                found.append((f"charts/{chart}", chart, caller, operations))
    umbrella = yaml.safe_load((CHARTS / "ghga-demo" / "values.yaml").read_text())
    for instance, chart in UMBRELLA_INSTANCES.items():
        for caller, operations in _callers(umbrella.get(instance) or {}).items():
            found.append((f"ghga-demo/{instance}", chart, caller, operations))
    return found


POLICIES = _policies()


def _routes(chart: str) -> set[tuple[str, str]]:
    """(METHOD, path) for every route in the chart's openapi.yaml, with each path
    parameter written as Istio's single-segment template {*}.
    """
    spec_file = MEMBER_PATHS[chart] / "openapi.yaml"
    assert spec_file.is_file(), f"{chart} has callers but no openapi.yaml"
    spec = yaml.safe_load(spec_file.read_text())
    return {
        (method.upper(), re.sub(r"\{[^}]+\}", "{*}", path))
        for path, item in spec["paths"].items()
        for method in item
        if method in {"get", "put", "post", "patch", "delete", "head", "options"}
    }


def test_policies_found():
    """Guards the checks below against silently finding nothing to check."""
    assert POLICIES


@pytest.mark.parametrize(
    "source, callee, caller, operations",
    POLICIES,
    ids=[f"{source}:{caller}" for source, _, caller, _ in POLICIES],
)
def test_caller_matches_the_api(source, callee, caller, operations):
    """Each caller is a known chart or umbrella instance, and each method and path
    it may use is a route of the callee's API.
    """
    assert caller in KNOWN_CALLERS, f"{source}: unknown caller {caller!r}"
    if operations is None or operations == [{"allowAll": True}]:
        return
    routes = _routes(callee)
    route_paths = {path for _, path in routes}
    for operation in operations:
        methods = operation.get("methods") or []
        for path in operation.get("paths") or []:
            assert path in route_paths, (
                f"{source}: {caller} may use {path}, which {callee} does not serve"
            )
            for method in methods:
                assert (method, path) in routes, (
                    f"{source}: {caller} may use {method} {path}, which {callee} does not serve"
                )
