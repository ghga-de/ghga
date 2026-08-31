#!/usr/bin/env python3
"""Refresh one Docker Hub repository's overview (full_description + description).

Shared by release.yaml's package-charts and update-image-overviews jobs - same
Docker Hub API shape either way (a repo name, a README, a short description),
differing only in which repo (<name>-chart vs <name>) and which README (a
generated chart README vs a hand-authored service one) each job passes in.

DOCKERHUB_BEARER_TOKEN must already be the short-lived token from the
/v2/auth/token exchange, not the raw DOCKERHUB_TOKEN secret - see release.yaml
for why a ghga org Access Token needs that exchange (and the namespace-scoped
API path below) instead of the personal-login flow. Fetched once per calling
job and reused across every repo in its loop, not re-fetched per repo here.

Usage: update_dockerhub_overview.py REPO README_PATH DESCRIPTION SOURCE_URL
"""

import json
import os
import sys
import urllib.request

from prep_dockerhub_overview import prep_overview


def main() -> None:
    repo, readme_path, description, source_url = sys.argv[1:5]
    namespace = os.environ["DOCKERHUB_USERNAME"]
    bearer_token = os.environ["DOCKERHUB_BEARER_TOKEN"]

    text = open(readme_path, encoding="utf-8").read()
    full_description = prep_overview(text, source_url)

    body = json.dumps(
        {"full_description": full_description, "description": description[:100]}
    ).encode()
    request = urllib.request.Request(
        f"https://hub.docker.com/v2/namespaces/{namespace}/repositories/{repo}",
        data=body,
        method="PATCH",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        },
    )
    with urllib.request.urlopen(request) as response:
        response.read()
    print(f"updated {namespace}/{repo} overview")


if __name__ == "__main__":
    main()
