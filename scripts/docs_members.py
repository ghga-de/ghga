#!/usr/bin/env python3
# PEP 723 inline metadata declares the one non-stdlib import, `pyyaml`, which reads the
# members' great-docs.yml. Run this with `uv run --script`, which resolves the block into a
# throwaway environment; the callers never `uv sync`, so a bare `python3` has nothing to
# import.
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Enumerate the members whose documentation the docs lane publishes.

Single source of truth for docs-publish.yaml and the justfile's `docs` recipe, so a
local build cannot drift from the published one (ADR-0021).

A member is documented iff it carries a `great-docs.yml`. That file is the build's
own config, so presence is the marker — a separate `[tool.ghga]` flag would be a
second source of truth able to disagree with it.

Each member is deployed under its own subpath of the one GitHub Pages site the
monorepo serves, named after its distribution: `<site>/<package>/`.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    uv run --script scripts/docs_members.py            # member paths, one per line
    uv run --script scripts/docs_members.py --json     # full records
    uv run --script scripts/docs_members.py --check    # verify the declared URLs
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import tomllib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The one Pages site this repo serves. Each documented member sits under it by name.
SITE_URL = "https://ghga-de.github.io/ghga"

# Same tiers as the uv workspace globs; a documented member can live in any of them.
TIERS = ("libs", "services", "tools")


def docs_members() -> list[dict]:
    """Every member carrying a great-docs.yml, ordered by path."""
    members = []
    for tier in TIERS:
        for config in sorted((ROOT / tier).glob("*/great-docs.yml")):
            member_dir = config.parent
            pyproject = member_dir / "pyproject.toml"
            if not pyproject.is_file():
                continue
            package = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"][
                "name"
            ]
            members.append(
                {
                    "path": member_dir.relative_to(ROOT).as_posix(),
                    "package": package,
                    # Trailing slash: great-docs writes site_url that way, and Pages
                    # serves the subpath as a directory.
                    "site_url": f"{SITE_URL}/{package}/",
                }
            )
    return members


def check(members: list[dict]) -> list[str]:
    """Report members whose great-docs.yml disagrees with its deploy subpath.

    Two keys have to name the same URL, and great-docs reads them in different
    places: `site_url` drives link and asset resolution, while the SEO pass reads
    `seo.canonical.base_url` and, when it is unset, GUESSES
    `https://<owner>.github.io/<repo>/` from `repo:` — which in a monorepo drops the
    member subpath. Either mistake is silent at build time and only shows up as wrong
    canonical links and sitemap entries on the deployed site, so the lane fails here
    instead.
    """
    errors = []
    for member in members:
        config = ROOT / member["path"] / "great-docs.yml"
        declared = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        expected = member["site_url"]
        found = {
            "site_url": declared.get("site_url"),
            "seo.canonical.base_url": declared.get("seo", {})
            .get("canonical", {})
            .get("base_url"),
        }
        for key, value in found.items():
            if value != expected:
                errors.append(
                    f"{member['path']}/great-docs.yml declares {key} {value!r}, "
                    f"but the docs lane deploys it to {expected!r}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="full records as JSON")
    parser.add_argument(
        "--check", action="store_true", help="verify site_url against the subpath"
    )
    args = parser.parse_args(argv)

    members = docs_members()

    if args.check:
        errors = check(members)
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1 if errors else 0

    if args.json:
        print(json.dumps(members))
    else:
        for member in members:
            print(member["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
