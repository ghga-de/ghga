#!/usr/bin/env python3
"""Create archive charts from values files using a simple template."""

from copy import deepcopy
import shutil
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

repo_root = Path(__file__).resolve().parents[1]
VALUES_DIR: Path = repo_root / "src" / "values"
OUTPUT_DIR: Path = repo_root / "charts"
CHARTS_YAML: Path = repo_root / "src" / "charts_app_versions.yaml"
CHART_TEMPLATE: Path = repo_root / "src" / "template"

YAML_PARSER = YAML()
YAML_PARSER.preserve_quotes = True


def find_values_file(values_dir: Path, chart: str) -> Path:
    yaml_path = values_dir / f"{chart}.yaml"
    yml_path = values_dir / f"{chart}.yml"

    if yaml_path.exists():
        return yaml_path
    return yml_path


def create_chart_from_template(
    chart: dict,
    values_file: Path,
) -> Path:
    chart_dir = OUTPUT_DIR / chart["name"]
    chart_dir.mkdir(parents=True, exist_ok=True)

    for item in CHART_TEMPLATE.iterdir():
        if item.is_dir():
            shutil.copytree(item, chart_dir / item.name, dirs_exist_ok=True)
        if item.is_file():
            shutil.copy2(item, chart_dir / item.name)

    with (CHART_TEMPLATE / "Chart.yaml").open("r", encoding="utf-8") as chart_yaml_file:
        chart_yaml = YAML_PARSER.load(chart_yaml_file)

    chart_yaml_ = deepcopy(chart_yaml)
    chart_yaml_["name"] = chart["name"]
    chart_yaml_["description"] = chart["description"]
    chart_yaml_["appVersion"] = DoubleQuotedScalarString(str(chart["appVersion"]))
    if "version" in chart:
        chart_yaml_["version"] = DoubleQuotedScalarString(str(chart["version"]))

    with (chart_dir / "Chart.yaml").open("w", encoding="utf-8") as chart_yaml_file:
        YAML_PARSER.dump(chart_yaml_, chart_yaml_file)

    shutil.copy2(values_file, chart_dir / "values.yaml")

    return chart_dir


def load_charts() -> dict:
    with CHARTS_YAML.open("r", encoding="utf-8") as charts_file:
        return YAML_PARSER.load(charts_file)


charts = load_charts()

created: list[Path] = []
for chart_name, chart in charts["charts"].items():
    values = find_values_file(VALUES_DIR, chart_name)
    created_path = create_chart_from_template(
        chart=chart,
        values_file=values,
    )
    print(f"Created chart for {chart_name} at {created_path}")
