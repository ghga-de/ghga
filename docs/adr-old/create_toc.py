#!/usr/bin/env python3

"""Create table of contents with all ADRs."""

import os


def get_toc():
    """Get table of contents with all ADRs."""
    adrs = [
        adr for adr in os.listdir(".") if adr.startswith("adr") and adr.endswith(".md")
    ]
    toc = []
    for adr in adrs:
        try:
            num = int(adr[3:6])
            if not 0 <= num < 1000:
                raise ValueError
        except ValueError:
            raise RuntimeError(f"Invalid ADR name {adr}") from None
        with open(adr) as adr_file:
            for line in adr_file:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            else:
                title = None
        if not title:
            raise RuntimeError(f"No title found in {adr}")
        entry = f"[{title}](./{adr})"
        toc.append((num, entry))
    return sorted(toc)


def main():
    """Print table of contents in Markdown format."""
    toc = get_toc()
    is_continuous = toc[-1][0] - toc[0][0] == len(toc) - 1
    for num, entry in get_toc():
        if is_continuous:
            print(f"{num}. {entry}")
        else:
            print(f"- ({num:003}) {entry}")


if __name__ == "__main__":
    main()
