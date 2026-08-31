#!/usr/bin/env python3
"""Refresh a batch of Docker Hub repositories' overviews (full_description +
description).

Shared by release.yaml's package-charts and update-image-overviews jobs - same
Docker Hub API shape either way (a repo name, a README, a short description),
differing only in which repo (<name>-chart vs <name>) and which README (a
generated chart README vs a hand-authored service one) each job passes in.

Reads a JSON array from stdin, one object per repo:
  {"repo": ..., "readme": <path>, "description": ..., "source_url": ...}

Authenticates once for the whole batch, not once per repo. DOCKERHUB_TOKEN
must be a ghga org Access Token (not a personal one) - confirmed against the
real API, and it needs two things a personal-user login doesn't:
  1. Exchange it for a short-lived bearer token via POST /v2/auth/token with
     {identifier, secret} (identifier = the org name for an OAT). NOT
     POST /v2/users/login/ with {username, password}: that's the personal-
     login flow, and it rejects org accounts outright regardless of
     credentials ("Cannot log into an organization account").
  2. Send that bearer token only against the *namespace-scoped* API path
     (/v2/namespaces/{org}/repositories/{repo}) - the legacy path
     (/v2/repositories/{org}/{repo}/) rejects every OAT-derived token outright
     per Docker's own docs (403 "token issued from organization access token
     is not allowed"), which is also why Basic Auth against the legacy path
     failed too, regardless of username or scope.
Verified end-to-end against the real ghga/wps-chart repo before landing this.
"""

import json
import os
import sys
import urllib.request

from prep_dockerhub_overview import prep_overview


def fetch_bearer_token(username: str, token: str) -> str:
    body = json.dumps({"identifier": username, "secret": token}).encode()
    request = urllib.request.Request(
        "https://hub.docker.com/v2/auth/token",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["access_token"]


def update_overview(
    namespace: str,
    repo: str,
    readme_path: str,
    description: str,
    source_url: str,
    bearer_token: str,
) -> None:
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


def main() -> None:
    items = json.load(sys.stdin)
    namespace = os.environ["DOCKERHUB_USERNAME"]
    bearer_token = fetch_bearer_token(namespace, os.environ["DOCKERHUB_TOKEN"])
    for item in items:
        update_overview(
            namespace,
            item["repo"],
            item["readme"],
            item["description"],
            item["source_url"],
            bearer_token,
        )


if __name__ == "__main__":
    main()
