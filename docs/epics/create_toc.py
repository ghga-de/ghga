#!/usr/bin/env python3

"""Create table of contents with all epics."""

import os


def get_toc():
    """Get table of contents with all epics."""
    epic_dirs = [d for d in os.listdir(".") if os.path.isdir(d) and d[:1].isdigit()]
    toc = []
    for epic_dir in epic_dirs:
        try:
            num = int(epic_dir.split("-", 1)[0])
            if not 0 <= num < 1000:
                raise ValueError
        except ValueError:
            raise RuntimeError(f"Invalid directory name {epic_dir}")
        spec_path = os.path.join(epic_dir, "technical_specification.md")
        if not os.path.exists(spec_path):
            raise RecursionError(f"No technical_specification.md found in {epic_dir}")
        for line in open(spec_path):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        else:
            title = None
        if not title:
            raise RuntimeError(f"No title found in {spec_path}")
        try:
            desc, name = title.rsplit("(", 1)
            desc = desc.rstrip()
            name = name[:-1].strip().title()
        except ValueError:
            name = desc = None
        if not name or not desc:
            raise RuntimeError(f"Unexpected title in {spec_path}")
        link = f"[{name}](./{spec_path})"
        toc.append((num, link, desc))
    return sorted(toc)


def main():
    """Print table of contents in Markdown format."""
    toc = get_toc()
    is_continuous = toc[-1][0] - toc[0][0] == len(toc) - 1
    for num, link, desc in get_toc():
        if is_continuous:
            print(f"{num}. {link}: {desc}")
        else:
            print(f"- ({num}) {link}: {desc}")


if __name__ == "__main__":
    main()
