#!/usr/bin/env python3
"""Prepare a README for Docker Hub's `full_description` field.

`prep_overview` is imported by update_dockerhub_overview.py, the script behind
both of release.yaml's overview-refresh jobs (chart repos and image repos), and
is the ONLY place either kind of README gets trimmed - never at generation
time, so the committed file and its GitHub rendering always show the whole
thing. Trimming only belongs here, at push time, since the ~25000-character
cap is a property of Docker Hub's one PATCH call, not of the file itself.

Docker Hub rejects a PATCH with full_description over that many characters
outright (docker/roadmap#475: a validation error, not silent truncation) -
confirmed live against a real, already-published chart repo's full_description
via the public API, which comes back at exactly 24998 characters ending in a
trim note: that publisher pre-truncates client-side before the PATCH, the same
thing this does, not something Docker Hub does for you server-side. LIMIT/
SAFE_LENGTH below leave real headroom under the cap: a README that lands just
under 25000 today grows past it the next time a field gains a longer
description, and by then this margin is the only thing standing between
"still fits" and the release workflow's PATCH call failing outright.

Neither generated chart READMEs nor hand-authored service READMEs under
services/*, tools/*, libs/* have a trim point built in, so a raw character
cutoff here could land mid-sentence or leave an odd number of ``` fences,
folding everything after into one unreadable code block. This cuts on the
last full line instead, closes a dangling fence, and appends a note pointing
at the untruncated file on GitHub.
"""

import sys

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
