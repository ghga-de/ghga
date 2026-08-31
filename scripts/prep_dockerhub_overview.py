#!/usr/bin/env python3
"""Prepare a README for Docker Hub's `full_description` field.

`prep_overview` is imported by update_dockerhub_overview.py, the script behind
both of release.yaml's overview-refresh jobs (chart repos and image repos).
Docker Hub rejects a PATCH with full_description over ~25000 characters
outright (a validation error, not silent truncation - see
deploy/src/create_charts.py's README_LENGTH_LIMIT comment for how that was
confirmed against the live API).

Generated chart READMEs already fit by construction (create_charts.py trims
its own parameter table on a row boundary before this ever runs); hand-authored
service READMEs under services/*, tools/*, libs/* don't have a trim point built
in, so a raw character cutoff here could land mid-sentence or leave an odd
number of ``` fences, folding everything after into one unreadable code block.
This cuts on the last full line instead, closes a dangling fence, and appends
a note pointing at the untruncated file on GitHub.
"""

import sys

# Same limit/margin as deploy/src/create_charts.py's README_LENGTH_LIMIT /
# README_SAFE_LENGTH - see that module for how the real Docker Hub cap was
# confirmed (~24998 chars in practice) and why a real margin below it matters.
LIMIT = 25000
SAFE_LENGTH = 22000


def prep_overview(text: str, source_url: str) -> str:
    """`text` unchanged if it fits; otherwise cut on a line boundary, with a
    fence closed if needed, plus a note pointing at `source_url` for the rest."""
    if len(text) <= LIMIT:
        return text

    note = (
        f"\n\n> This README is longer than Docker Hub's {LIMIT}-character overview"
        " limit, so it has been cut short here. Read the rest on GitHub:"
        f" {source_url}"
    )
    kept = text[: SAFE_LENGTH - len(note)]
    if "\n" in kept:
        kept = kept.rsplit("\n", 1)[0]
    if kept.count("```") % 2:
        kept += "\n```"
    return kept + note


def main() -> None:
    readme_path, source_url = sys.argv[1], sys.argv[2]
    text = open(readme_path, encoding="utf-8").read()
    sys.stdout.write(prep_overview(text, source_url))


if __name__ == "__main__":
    main()
