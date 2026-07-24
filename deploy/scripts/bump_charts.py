from pathlib import Path
from ruamel.yaml import YAML
from semver import VersionInfo
import requests
import argparse
import subprocess

"""
Helm Chart Version Bumper

This script automates the process of bumping Helm chart versions based on the latest
published versions available in a Helm repository. It supports version validation,
computing version differences, and updating dependencies if needed.

Dependencies:
    - pathlib
    - ruamel.yaml
    - semver
    - requests
    - argparse
    - subprocess

Usage:
    python bump_charts.py --chart-dir <chart_directory> --library-chart-version <version>

Arguments:
    --chart-dir (str): Path to the directory containing Helm charts to be bumped.
    --library-chart-version (str): Version of the ghga-common library chart to use.

Global Variables:
    DRY_MODE (bool): If True, prevents actual file modifications.
    VALIDATE (bool): If True, ensures version consistency before applying changes.

Functions:
    fetch_helm_repo_index(helm_repo_url: str) -> dict
        Fetches and parses the index.yaml file from the given Helm repository URL.
    
    get_latest_published_version(helm_index: dict, chart_name: str) -> dict | None
        Retrieves the latest published appVersion and chart version from the Helm repository.
    
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
    - Update Chart.yaml files with the new versions if needed.
    - If dependencies need updating, bump the ghga-common library version.

"""

DRY_MODE = False
VALIDATE = False

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
            new_version = new_version.replace(
                **{part: getattr(base_version, part) + 1}
            )
            return new_version
        else:
            new_version = new_version.replace(**{part: getattr(base_version, part)})


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument(
        "--chart-dir",
        type=str,
        help="A directory containing Charts which should be bumped",
        default="charts/file-services-backend",
    )  # Optional argument
    parser.add_argument(
        "--library-chart-version",
        type=str,
        help="Library chart version which should be used",
        default="",
    )  # Optional argument

    # Parse arguments
    args = parser.parse_args()

    if "base" in args.chart_dir:
        print("Skipping bumping of base")
        exit(0)

    print("Bumping Helm charts in", args.chart_dir)
    helm_repo_url = "https://ghga-de.github.io/charts"

    # Fetch latest published appVersion
    helm_index = fetch_helm_repo_index(helm_repo_url)

    # Get all charts in a directory
    chart_files = list(Path(args.chart_dir).rglob("Chart.yaml"))
    charts = list(zip(chart_files, get_charts(chart_files)))
    
    if not args.library_chart_version or args.library_chart_version == "0.0.0":
        latest_ghga_common = VersionInfo.parse(
            helm_index["entries"]["ghga-common"][0]["version"]
        )
    else:
        latest_ghga_common = VersionInfo.parse(args.library_chart_version)

    diffs_app_version, diffs_library_version, latest_versions = [], [], []
    diff_version = []
    for chart_file, chart in charts:
        current_app_version = VersionInfo.parse(chart.get("appVersion"))
        current_version = VersionInfo.parse(chart.get("version"))
        
        latest = get_latest_published_version(helm_index, chart["name"])
        if latest:
            latest_app_version = latest["appVersion"]
            latest_version = latest["version"]
        # Chart doen't exist yet in the index.yaml
        else:
            latest_app_version = VersionInfo.parse("0.0.0")
            latest_version = VersionInfo.parse("0.0.0")
        
        latest_versions.append(latest_version)
        print(f"Latest published version for {chart['name']}: {latest_version}")

        if current_version > latest_version:
            print(
                f"Version {current_version} is newer than latest published {latest_version} for {chart['name']}"
            )
            diff_version.append(get_version_diff(current_version, latest_version))

        if current_app_version > latest_app_version:
            print(
                f"AppVersion {current_app_version} is newer than latest published {latest_app_version} for {chart['name']}"
            )
            diffs_app_version.append(get_version_diff(current_app_version, latest_app_version))

        for dep in chart.get("dependencies"):
            if dep.get("name") == "ghga-common":
                current_ghga_common = VersionInfo.parse(dep.get("version"))

        if latest_ghga_common > current_ghga_common:
            print(
                f"Library version {current_ghga_common} is older than latest published {latest_ghga_common} for {chart['name']}"
            )
            diffs_library_version.append(
                get_version_diff(current_ghga_common, latest_ghga_common)
            )

    if not diffs_app_version and not diffs_library_version and not diff_version:
        print("All charts are up-to-date.")
        exit(0)

    if VALIDATE:
        if not all(version == latest_versions[0] for version in latest_versions):
            raise ValueError("Versions are inconsistent")

    if diffs_app_version:
        max_diff = max(diffs_app_version)
    elif diffs_library_version:
        max_diff = max(diffs_library_version)
    elif diff_version:
        print("Diff in Chart version, doing nothing.")
        exit(0)
    print(f"Max diff: {max_diff}")

    latest_versions.sort()
    new_version = bump_version(latest_versions.pop(), max_diff)

    # Update the version in the Chart.yaml
    for chart_file, chart in charts:
        print(f"Bumping {chart['name']} from {chart['version']} to {new_version}")

        chart["version"] = str(new_version)

        if diffs_app_version or diff_version:
            print("Updating appVersion, skipping dependency update")
            # Dump to files
            if not DRY_MODE:
                with Path(chart_file).open("w", encoding="utf-8") as f:
                    yaml.dump(chart, f)
            continue

        elif diffs_library_version:
            for dep in chart.get("dependencies"):
                if dep.get("name") == "ghga-common":
                    if dep["version"] != str(latest_ghga_common):
                        print(
                            f"Bumping {str(chart_file.parent)} deps ghga-common from {dep['version']} to {latest_ghga_common}"
                        )
                        dep["version"] = str(latest_ghga_common)
                        # Dump to files
                        if not DRY_MODE:
                            with Path(chart_file).open("w", encoding="utf-8") as f:
                                yaml.dump(chart, f)
                        subprocess.run(
                            [
                                "helm",
                                "dependency",
                                "update",
                                str(chart_file.parent),
                                "--skip-refresh",
                            ]
                        )
