import yaml
import semver
from pathlib import Path


""""
This scripts update all charts in the CHARTS_DIR directory to the latest version of the library chart.
"""

CHARTS_DIR = Path("charts")  # Base directory for Helm charts
LIBRARY_CHART_NAME = "ghga-common"


def read_chart_yaml(chart_path):
    """Reads the Chart.yaml file and returns its contents."""
    chart_file = chart_path / "Chart.yaml"
    with chart_file.open("r") as f:
        return yaml.safe_load(f)


def update_version_in_file(chart_path, target, old_version, new_version):
    """Replaces the old version with the new version in Chart.yaml without removing comments."""
    chart_file = chart_path / "Chart.yaml"
    content = chart_file.read_text().splitlines()
    match target:
        case "chart":
            line = content[7]
            if f"version: {old_version}" not in line:
                raise ValueError(f"Wrong line number for version in {chart_path.name}")
            content[7] = line.replace(old_version, new_version)
        case "library":
            line = content[21]
            if f"version: {old_version}" not in line:
                raise ValueError(f"Wrong line number for version in {chart_path.name}")
            content[21] = line.replace(old_version, new_version)
        case _:
            raise ValueError(f"Invalid target: {target}")
    chart_file.write_text("\n".join(content))
    print(f"Updated {chart_path.name} to version {new_version}")


def get_new_version(current_version, old_lib_version, new_lib_version):
    """Determines how to bump the version based on library chart version change."""
    parsed_current = semver.VersionInfo.parse(current_version)
    parsed_old_lib = semver.VersionInfo.parse(old_lib_version)
    parsed_new_lib = semver.VersionInfo.parse(new_lib_version)

    if parsed_new_lib.major > parsed_old_lib.major:
        return str(parsed_current.bump_major())
    elif parsed_new_lib.minor > parsed_old_lib.minor:
        return str(parsed_current.bump_minor())
    elif parsed_new_lib.patch > parsed_old_lib.patch:
        return str(parsed_current.bump_patch())

    return current_version  # No change if library version is the same


def update_library_dependency(chart_path, library_version):
    """Updates the library chart dependency in Chart.yaml and returns old version."""
    chart_data = read_chart_yaml(chart_path)

    dependencies = chart_data.get("dependencies", [])
    library_old_version = None
    updated = False

    for dep in dependencies:
        if dep.get("name") == LIBRARY_CHART_NAME:
            library_old_version = dep["version"]
            if library_old_version != library_version:
                dep["version"] = library_version
                updated = True

    if updated:
        update_version_in_file(chart_path, "library", library_old_version, library_version)
        print(f"Updated {chart_path.name} dependency to library version {library_version}")

    return library_old_version


def update_chart_versions():
    """Iterates through all charts, updates dependencies, and bumps versions."""
    library_chart_path = CHARTS_DIR / LIBRARY_CHART_NAME
    library_new_version = read_chart_yaml(library_chart_path).get("version")

    if not library_new_version:
        print("Error: Could not determine the latest library chart version!")
        return

    print(f"Latest library chart version: {library_new_version}")

    for chart_path in CHARTS_DIR.iterdir():
        if chart_path.is_dir() and chart_path.name != LIBRARY_CHART_NAME:
            chart_yaml = read_chart_yaml(chart_path)
            current_version = chart_yaml.get("version")
            
            if not current_version:
                print(f"Skipping {chart_path.name}, no valid version found.")
                continue

            library_old_version = update_library_dependency(chart_path, library_new_version)

            if library_old_version:
                new_version = get_new_version(current_version, library_old_version, library_new_version)
                if new_version != current_version:
                    chart_yaml["version"] = new_version
                    update_version_in_file(chart_path, "chart", current_version, new_version)
                    print(f"Bumped {chart_path.name} version to {new_version}")

if __name__ == "__main__":
    update_chart_versions()
