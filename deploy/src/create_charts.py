#!/usr/bin/env python3
"""Generate the per-service Helm charts from workspace metadata.

Chart identity (name, description) and the derivable runtime facts (image
reference, executable, configPrefix, command style) come from the workspace
members enumerated by scripts/image_members.py — the same source the release
workflow uses. Genuine deployment knowledge lives in each member's
chart-values.yaml, co-located with the member.

Auxiliary charts (no workspace member behind them) are listed in
auxiliary_charts.yaml and keep hand-maintained values in values/<name>.yaml.

Conventions baked into the derived values:
- chart name == package name == image name == console script (ADR-0014)
- the monorepo images are shell-less hardened bases -> commandStyle=exec,
  no command prefix (executables resolve via the image PATH)
- image.tag stays empty so the Bitnami image helper falls back to the chart's
  appVersion == the platform version (ADR-0004)
"""

import argparse
import shutil
import sys
from copy import deepcopy
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

DEPLOY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEPLOY_ROOT.parent
VALUES_DIR = DEPLOY_ROOT / "src" / "values"
OUTPUT_DIR = DEPLOY_ROOT / "charts"
AUX_CHARTS_YAML = DEPLOY_ROOT / "src" / "auxiliary_charts.yaml"
CHART_TEMPLATE = DEPLOY_ROOT / "src" / "template"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from image_members import image_members

YAML_PARSER = YAML()
YAML_PARSER.preserve_quotes = True

DERIVED_HEADER = """\
# ---- derived from workspace metadata by create_charts.py — do not edit -----------------
"""

VALUES_SEPARATOR = """\

# ---- deployment values ({source}) -----------------
"""


def derived_values(member: dict, registry: str) -> dict:
    """Values derived from workspace metadata for one member chart."""
    registry_host, _, repo_prefix = registry.partition("/")
    values: dict = {
        "image": {
            "registry": registry_host,
            "repository": f"{repo_prefix}/{member['package']}"
            if repo_prefix
            else member["package"],
        },
        "configPrefix": member["package"].replace("-", "_"),
        "commandStyle": "exec",
        "commandPrefix": "",
    }
    if member["kind"] == "python":
        # console script == package name (enforced at image build); frontend images
        # run via their ENTRYPOINT instead, so no executable is set for them
        values["executable"] = member["package"]
    return values


def stamp_chart(
    name: str,
    description: str,
    version: str,
    app_version: str,
    values_text: str,
) -> Path:
    """Stamp one chart from the template with the given identity and values."""
    chart_dir = OUTPUT_DIR / name
    if chart_dir.exists():
        shutil.rmtree(chart_dir)
    shutil.copytree(CHART_TEMPLATE, chart_dir)

    with (CHART_TEMPLATE / "Chart.yaml").open("r", encoding="utf-8") as chart_yaml_file:
        chart_yaml = YAML_PARSER.load(chart_yaml_file)
    chart_yaml = deepcopy(chart_yaml)
    chart_yaml["name"] = name
    chart_yaml["description"] = description
    chart_yaml["version"] = DoubleQuotedScalarString(version)
    chart_yaml["appVersion"] = DoubleQuotedScalarString(app_version)
    with (chart_dir / "Chart.yaml").open("w", encoding="utf-8") as chart_yaml_file:
        YAML_PARSER.dump(chart_yaml, chart_yaml_file)

    (chart_dir / "values.yaml").write_text(values_text)
    return chart_dir


def member_values_text(member: dict, registry: str) -> str:
    """Compose a member chart's values.yaml: derived block + chart-values.yaml."""
    buffer = StringIO()
    buffer.write(DERIVED_HEADER)
    YAML_PARSER.dump(derived_values(member, registry), buffer)

    values_file = REPO_ROOT / member["path"] / "chart-values.yaml"
    if values_file.is_file():
        buffer.write(
            VALUES_SEPARATOR.format(source=f"{member['path']}/chart-values.yaml")
        )
        buffer.write(values_file.read_text())
    else:
        print(
            f"note: {member['path']} has no chart-values.yaml; using library defaults"
        )
    return buffer.getvalue()


def main() -> None:
    """Regenerate all charts (workspace members + auxiliary)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default="0.0.0+dev",
        help="platform version stamped as chart version and appVersion (ADR-0004)",
    )
    parser.add_argument(
        "--registry",
        default="ghcr.io/ghga-de/ghga",
        help="image registry root; the package name is appended per member",
    )
    args = parser.parse_args()

    for member in image_members():
        chart_dir = stamp_chart(
            name=member["package"],
            description=member["description"] or member["package"],
            version=args.version,
            app_version=args.version,
            values_text=member_values_text(member, args.registry),
        )
        print(f"Created chart for {member['package']} at {chart_dir}")

    with AUX_CHARTS_YAML.open("r", encoding="utf-8") as aux_file:
        aux_charts = YAML_PARSER.load(aux_file)
    for name, chart in aux_charts["charts"].items():
        values_file = VALUES_DIR / f"{name}.yaml"
        chart_dir = stamp_chart(
            name=name,
            description=chart["description"],
            version=str(chart.get("version", chart["appVersion"])),
            app_version=str(chart["appVersion"]),
            values_text=values_file.read_text(),
        )
        print(f"Created auxiliary chart for {name} at {chart_dir}")


if __name__ == "__main__":
    main()
