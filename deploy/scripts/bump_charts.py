from pathlib import Path
from ruamel.yaml import YAML
import semver
import requests
import argparse

"""Bump all Helm charts in a directory according to the largest service version difference or library chart update."""

DRY_MODE = False

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
) -> semver.VersionInfo:
    """Extracts the latest appVersion from the Helm repository index.yaml."""
    if "entries" not in helm_index or chart_name not in helm_index["entries"]:
        return None

    versions = []
    for entry in helm_index["entries"][chart_name]:
        app_version = entry.get("appVersion")
        if app_version and semver.VersionInfo.is_valid(app_version):
            versions.append(semver.VersionInfo.parse(app_version))

    return max(versions) if versions else None


def get_charts(chart_files):
    """Extracts charts in a directory."""
    charts = []

    for chart_file in chart_files:
        chart = yaml.load(Path(chart_file).read_text())
        charts.append(chart)

    return charts


def bump_version(
    base_version: semver.VersionInfo, version_diff: semver.VersionInfo
) -> semver.VersionInfo:
    """Applies a semantic version difference to a base version."""

    # Apply the biggest version change
    new_version = semver.VersionInfo(
        base_version.major + version_diff.major,
        base_version.minor + version_diff.minor,
        base_version.patch + version_diff.patch,
    )

    return new_version


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="A simple argparse example")

    # Add arguments
    parser.add_argument(
        "--chart-dir",
        type=str,
        help="A directory containing Charts which should be bumped",
        default="charts/file-services-backend",
    )  # Optional argument
    parser.add_argument(
        "--current-version",
        type=str,
        help="Current version which should be bumped",
        default="7.0.0",
    )  # Optional argument

    # Parse arguments
    args = parser.parse_args()

    if "ghga-common" in args.chart_dir:
        print("Skipping bumping of ghga-common charts")
        exit(0)

    print("Bumping Helm charts in", args.chart_dir)
    helm_repo_url = "https://ghga-de.github.io/charts"

    # Fetch latest published appVersion
    helm_index = fetch_helm_repo_index(helm_repo_url)

    # Get all charts in a directory
    chart_files = list(Path(args.chart_dir).rglob("Chart.yaml"))

    charts = list(zip(chart_files, get_charts(chart_files)))
    latest_ghga_common = semver.VersionInfo.parse(
        helm_index["entries"]["ghga-common"][0]["version"]
    )

    diffs_app_version, diffs_library_version, current_versions = [], [], []
    for chart_file, chart in charts:
        current_versions.append(semver.VersionInfo.parse(chart.get("version")))
        current = semver.VersionInfo.parse(chart.get("appVersion"))
        latest = get_latest_published_version(helm_index, chart["name"])

        if current > latest:
            print(
                f"AppVersion {current} is newer than latest published {latest} for {chart['name']}"
            )
            if current.major > latest.major:
                diff = semver.VersionInfo(
                    current.major - latest.major,
                    0,
                    0,
                )
            elif current.minor > latest.minor:
                diff = semver.VersionInfo(
                    0,
                    current.minor - latest.minor,
                    0,
                )
            elif current.patch > latest.patch:
                diff = semver.VersionInfo(
                    0,
                    0,
                    current.patch - latest.patch,
                )
            diffs_app_version.append(diff)

        # Check for ghga-common updates

        for dep in chart.get("dependencies"):
            if dep.get("name") == "ghga-common":
                current_ghga_common = semver.VersionInfo.parse(dep.get("version"))

        if latest_ghga_common > current_ghga_common:
            print(
                f"Library version {current_ghga_common} is older than latest published {latest_ghga_common} for {chart['name']}"
            )
            if latest_ghga_common.major > current_ghga_common.major:
                diff = semver.VersionInfo(
                    latest_ghga_common.major - current_ghga_common.major,
                    0,
                    0,
                )
            elif latest_ghga_common.minor > current_ghga_common.minor:
                diff = semver.VersionInfo(
                    0,
                    latest_ghga_common.minor - current_ghga_common.minor,
                    0,
                )
            elif latest_ghga_common.patch > current_ghga_common.patch:
                diff = semver.VersionInfo(
                    0,
                    0,
                    latest_ghga_common.patch - current_ghga_common.patch,
                )
            
            diffs_library_version.append(diff)

    if not diffs_app_version and not diffs_library_version:
        print("All charts are up-to-date.")
        exit(0)

    if not all(version == current_versions[0] for version in current_versions):
        raise ValueError("Versions are inconsistent")

    max_diff = max(diffs_app_version + diffs_library_version)
    print(f"Max diff: {max_diff}")
    
    new_version = bump_version(current_versions.pop(), max_diff)
    
    # Update the version in the Chart.yaml
    for chart_file, chart in charts:
        print(f"Bumping {chart['name']} from {chart['version']} to {new_version}")
        chart["version"] = str(new_version)

        if diffs_library_version:
            for dep in chart.get("dependencies"):
                if dep.get("name") == "ghga-common":
                    print(
                        f"Bumping ghga-common from {dep['version']} to {latest_ghga_common} requires to run helm dependency update"
                    )
                    dep["version"] = str(latest_ghga_common)

        # Dump to files
        if not DRY_MODE:
            with Path(chart_file).open("w", encoding="utf-8") as f:
                yaml.dump(chart, f)
