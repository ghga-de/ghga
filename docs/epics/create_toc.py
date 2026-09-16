#!/usr/bin/env python3

"""Create table of contents with all epics."""

import os
import re

EPIC_NAME = re.compile(r"^epic-(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*$")


def get_spec_paths():
    """Get the spec file of every epic, by epic name.

    An epic without supporting files is a single Markdown file; one with them is a
    directory holding a README.md next to those files.
    """
    specs = {}
    for entry in os.listdir("."):
        name = entry[:-3] if entry.endswith(".md") else entry
        if not EPIC_NAME.match(name):
            continue
        if os.path.isdir(entry):
            spec_path = os.path.join(entry, "README.md")
            if not os.path.exists(spec_path):
                raise RuntimeError(f"No README.md found in {entry}")
        else:
            spec_path = entry
        if name in specs:
            raise RuntimeError(f"Epic {name} exists as a file and as a directory")
        specs[name] = spec_path
    return specs


def get_toc():
    """Get table of contents with all epics."""
    toc = []
    for name, spec_path in get_spec_paths().items():
        num = int(EPIC_NAME.match(name).group(1))
        with open(spec_path) as spec_file:
            for line in spec_file:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            else:
                title = None
        if not title:
            raise RuntimeError(f"No title found in {spec_path}")
        try:
            desc, code_name = title.rsplit("(", 1)
            desc = desc.rstrip()
            code_name = code_name[:-1].strip().title()
        except ValueError:
            code_name = desc = None
        if not code_name or not desc:
            raise RuntimeError(f"Unexpected title in {spec_path}")
        link = f"[{code_name}](./{spec_path})"
        toc.append((num, link, desc))
    return sorted(toc)


def main():
    """Print table of contents in Markdown format."""
    toc = get_toc()
    is_continuous = toc[-1][0] - toc[0][0] == len(toc) - 1
    for num, link, desc in toc:
        if is_continuous:
            print(f"{num}. {link}: {desc}")
        else:
            print(f"- ({num}) {link}: {desc}")


if __name__ == "__main__":
    main()
