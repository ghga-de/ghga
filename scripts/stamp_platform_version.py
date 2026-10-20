#!/usr/bin/env python3
"""Stamp the platform version onto an installed environment (ADR-0027, ADR-0046).

Run INSIDE an image build, with the image's interpreter, AFTER dependency
installation (`uv sync`) — never against a development venv you care about.

Two operations on the workspace-internal distributions, those installed from
workspace source (identified by a `file://` `direct_url.json`):

1. A platform-lane member declares the placeholder version `0.0.0`; its
   dist-info `Version:` is rewritten to the platform version. Services surface
   their version via `importlib.metadata` (OpenAPI info etc.), so the running
   container reports the platform version. This covers the released member,
   the platform-lane libraries it uses, and every member of the mono image.
2. Every other one (the PyPI lane) gets a PEP 440 local suffix:
   `8.6.0` -> `8.6.0+ghga.<platform-version>`. Dependency constraints remain
   satisfied (local versions compare equal to their base), scanner/SBOM
   metadata stays coherent, and local versions cannot be pushed to PyPI by
   design.

`RECORD` entries for rewritten `METADATA` files are updated so the dist-info
stays internally consistent. The script is idempotent.

Usage (in a Dockerfile; `--package` fails the build if that member was not stamped):
    python /scripts/stamp_platform_version.py --version "$PLATFORM_VERSION" \
        [--package "$PACKAGE"]

stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import sys
from importlib.metadata import Distribution, distributions
from pathlib import Path

VERSION_LINE = re.compile(r"^Version: .*$", flags=re.MULTILINE)

# What a platform-lane member declares in its pyproject.toml (ADR-0046)
PLACEHOLDER = "0.0.0"


def _record_entry(dist_info: Path, metadata: Path) -> str:
    """Compute the RECORD line fields for a metadata file."""
    data = metadata.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    rel = f"{dist_info.name}/{metadata.name}"
    return f"{rel},sha256={digest.decode()},{len(data)}"


def _update_record(dist_info: Path, metadata: Path) -> None:
    record = dist_info / "RECORD"
    if not record.is_file():
        return
    rel = f"{dist_info.name}/{metadata.name}"
    rows = list(csv.reader(io.StringIO(record.read_text())))
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    for row in rows:
        if row and row[0] == rel:
            writer.writerow(_record_entry(dist_info, metadata).split(","))
        else:
            writer.writerow(row)
    record.write_text(out.getvalue())


def _rewrite_version(dist: Distribution, new_version: str) -> str:
    # no public path accessor on Distribution
    dist_info = Path(str(dist._path))  # type: ignore[attr-defined]
    metadata = dist_info / "METADATA"
    text = metadata.read_text()
    if not VERSION_LINE.search(text):
        raise RuntimeError(f"no Version field in {metadata}")
    metadata.write_text(VERSION_LINE.sub(f"Version: {new_version}", text, count=1))
    _update_record(dist_info, metadata)
    return new_version


def _canonical(name: str) -> str:
    return name.lower().replace("_", "-")


def _is_workspace_install(dist: Distribution) -> bool:
    """Whether a distribution was installed from workspace source (not a registry)."""
    raw = dist.read_text("direct_url.json")
    if not raw:
        return False
    try:
        url = json.loads(raw).get("url", "")
    except json.JSONDecodeError:
        return False
    return url.startswith("file://")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True, help="platform version, e.g. 17.0.0")
    ap.add_argument(
        "--package",
        help="distribution name of the released member, checked to be stamped",
    )
    args = ap.parse_args(argv)

    suffix = f"+ghga.{args.version.replace('+', '.')}"
    stamped: list[str] = []
    suffixed = 0

    for dist in distributions():
        if not _is_workspace_install(dist):
            continue
        name = _canonical(dist.metadata["Name"] or "")
        if dist.version == PLACEHOLDER:
            _rewrite_version(dist, args.version)
            print(f"stamped   {name}: {args.version}")
            stamped.append(name)
        elif dist.version == args.version:
            stamped.append(name)  # by an earlier run
        elif "+" in dist.version:
            continue  # suffixed by an earlier run, or intentionally local
        else:
            # print the returned version: `dist.version` rereads the rewritten METADATA
            print(f"suffixed  {name}: {_rewrite_version(dist, dist.version + suffix)}")
            suffixed += 1

    if args.package and _canonical(args.package) not in stamped:
        print(
            f"error: package {args.package!r} not found in this environment"
            f" with the placeholder version {PLACEHOLDER}",
            file=sys.stderr,
        )
        return 1
    print(f"done: {len(stamped)} stamped, {suffixed} workspace libs suffixed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
