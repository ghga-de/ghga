from pathlib import Path
from ruamel.yaml import YAML
from semver import VersionInfo
import requests
import os
import subprocess
import shutil

"""
Helm Chart Version Bumper

This script automates bumping Helm chart versions based on the latest published
versions in a Helm repository. It supports version validation, computing version
differences, and updating dependencies as needed.

Dependencies:
    - pathlib
    - ruamel.yaml
    - semver
    - requests
    - subprocess
    - shutil
    - os

Usage:
    python library_update.py

Functions:
    fetch_helm_repo_index(helm_repo_url: str) -> dict
        Fetches and parses the `index.yaml` file from a Helm repository URL.

    get_latest_published_version(helm_index: dict, chart_name: str) -> dict | None
        Retrieves the latest published chart version and appVersion from a Helm repository.

    get_charts(chart_files: list[Path]) -> list[dict]
        Loads and parses Helm chart YAML files from a list of file paths.

    get_version_diff(version_a: VersionInfo, version_b: VersionInfo) -> VersionInfo
        Computes the semantic version difference between two versions.

    bump_version(base_version: VersionInfo, version_diff: VersionInfo) -> VersionInfo
        Increments a base version by a calculated version difference.

Main Execution Flow:
    - Fetch the Helm repository index.
    - Retrieve the latest published versions for charts.
    - Compare current versions with the latest published ones.
    - Compute version differences and determine the required version bump.
    - Update Chart.yaml files with new versions if needed.
    - If dependencies need updating, bump the ghga-common library version.
"""

yaml = YAML()
yaml.preserve_quotes = True  # Preserve formatting


def fetch_helm_repo_index(helm_repo_url):
    """Fetches the index.yaml from a Helm repository."""
    index_url = f"{helm_repo_url.rstrip('/')}/index.yaml"
    response = requests.get(index_url, timeout=10)

    if response.status_code == 200:
        return yaml.load(response.text)
    else:
        raise ValueError(f"Failed to fetch {index_url}: {response.status_code}")


def get_latest_published_version(
    helm_index: dict[str, any], chart_name: str
) -> tuple[VersionInfo, VersionInfo] | None:
    """Extracts the latest appVersion from the Helm repository index.yaml."""
    if "entries" not in helm_index or chart_name not in helm_index["entries"]:
        return None

    versions = []
    app_versions = []
    for entry in helm_index["entries"][chart_name]:
        app_version = entry.get("appVersion")
        if app_version and VersionInfo.is_valid(app_version):
            app_versions.append(VersionInfo.parse(app_version))
        version = entry.get("version")
        if app_version and VersionInfo.is_valid(version):
            versions.append(VersionInfo.parse(version))

    return {
        "version": max(versions) if versions else None,
        "appVersion": max(app_versions) if app_versions else None,
    }


def get_charts(chart_files: list[Path]) -> list[dict[str, any]]:
    """Extracts charts in a directory."""
    charts = []
    for chart_file in chart_files:
        chart = yaml.load(Path(chart_file).read_text())
        charts.append(chart)
    return charts


def get_version_diff(version_a: VersionInfo, version_b: VersionInfo) -> VersionInfo:
    """Calculates the absolute version difference between two versions."""
    diff = VersionInfo.parse("0.0.0")
    for part in ["major", "minor", "patch", "prerelease"]:
        if getattr(version_a, part) != getattr(version_b, part):
            if part == "prerelease":
                diff = diff.bump_patch()
            else:
                diff = diff.replace(
                    **{part: abs(getattr(version_a, part) - getattr(version_b, part))}
                )
            print(f"Diff between {version_a} and {version_b}: {diff}")
            break
    return diff


def bump_version(base_version: VersionInfo, version_diff: VersionInfo) -> VersionInfo:
    """Applies a semantic version difference to a base version."""
    new_version = VersionInfo.parse("0.0.0")
    for part in ["major", "minor", "patch"]:
        if getattr(version_diff, part) > 0:
            new_version = new_version.replace(**{part: getattr(base_version, part) + 1})
            return new_version
        else:
            new_version = new_version.replace(**{part: getattr(base_version, part)})
    # Nothing changed
    return base_version

if __name__ == "__main__":
    # Create the parser
    chart_dir = os.getenv("CHART_DIR", "archive/file-services-backend")
    dev = os.getenv("DEV", False)

    helm_repo_url = "https://ghga-de.github.io/charts"
    # Fetch helm index
    helm_index = fetch_helm_repo_index(helm_repo_url)

    if dev:
        print("Running in development mode")
        current_ghga_common = get_charts([Path("base/ghga-common/Chart.yaml")])[0]
        latest_ghga_common = VersionInfo.parse(current_ghga_common.get("version"))

    else:
        ghga_common_repo = helm_repo_url
        # Get the latest ghga-common version
        latest_ghga_common = VersionInfo.parse(
            helm_index["entries"]["ghga-common"][0]["version"]
        )

    if "base" in chart_dir:
        print("Skipping bumping of base")
        exit(0)

    print("Bumping Helm charts in", chart_dir)

    # Get all charts in a directory
    chart_files = list(Path(chart_dir).rglob("Chart.yaml"))
    charts = list(zip(chart_files, get_charts(chart_files)))

    diffs_library_version, latest_versions = [], []

    # They are all the same
    chart_file, chart = charts[0]
    current_version = VersionInfo.parse(chart.get("version"))

    latest = get_latest_published_version(helm_index, chart["name"])
    latest_version = latest["version"]

    print(f"Latest published version for {chart['name']}: {latest_version}")

    current_ghga_common = VersionInfo.parse(next(
        dep
        for dep in chart.get("dependencies")
        if dep.get("name") == "ghga-common"
    ).get("version"))

    if latest_ghga_common > current_ghga_common or dev:
        print(
            f"Library version {current_ghga_common} is older than latest published {latest_ghga_common} for {chart['name']}"
        )
        
        max_diff = get_version_diff(current_ghga_common, latest_ghga_common)
        print(f"Max diff: {max_diff}")
    else:
        print("All charts are up-to-date.")
        exit(0)

    # Get new version
    new_version = bump_version(latest_version, max_diff)

    # Update the version in the Chart.yaml
    first_processed_chart = None
    for chart_file, chart in charts:
        print(f"Bumping {chart['name']} from {chart['version']} to {new_version}")

        chart["version"] = str(new_version)

        i, ghga_common = next(
            (i, dep)
            for i, dep in enumerate(chart.get("dependencies"))
            if dep.get("name") == "ghga-common"
        )
        if (ghga_common and ghga_common["version"] != str(latest_ghga_common)) or dev:
            print(
                f"Bumping {str(chart_file.parent)} deps ghga-common from {ghga_common['version']} to {latest_ghga_common}"
            )
            ghga_common["version"] = str(latest_ghga_common)

            if dev:
                rel_path = os.path.relpath("base/ghga-common", chart_file.parent)
                ghga_common_repo = f"file://{rel_path}"

            ghga_common["repository"] = ghga_common_repo
            with Path(chart_file).open("w", encoding="utf-8") as f:
                yaml.dump(chart, f)

            if not first_processed_chart:
                first_processed_chart = chart
                # Update dependencies is very slow, therefore we only run it once
                subprocess.run(
                    [
                        "helm",
                        "dependency",
                        "update",
                        str(chart_file.parent),
                        "--skip-refresh",
                    ]
                )

                lock_file = Path(chart_file.parent) / "Chart.lock"
                ghga_common_tgz = (
                    Path(chart_file.parent)
                    / "charts"
                    / f"ghga-common-{latest_ghga_common}.tgz"
                )
                print(lock_file, ghga_common_tgz)
            else:
                shutil.copy(lock_file, Path(chart_file.parent) / "Chart.lock")
                shutil.copy(
                    ghga_common_tgz,
                    Path(chart_file.parent)
                    / "charts"
                    / f"ghga-common-{latest_ghga_common}.tgz",
                )
                (
                    Path(chart_file.parent)
                    / "charts"
                    / f"ghga-common-{current_ghga_common}.tgz"
                ).unlink(missing_ok=False)
