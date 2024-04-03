#!/usr/bin/env python3

# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import sys
from collections.abc import Generator
from datetime import datetime

import yaml
from git import Repo
from pydantic import BaseModel


class Service(BaseModel):
    name: str
    image: str
    tag: str
    modified: bool = False

    def __hash__(self):
        return hash((self.name, self.image, self.tag, self.modified))

    def __eq__(self, other):
        if isinstance(other, Service):
            return (
                self.name == other.name
                and self.image == other.image
                and self.tag == other.tag
                and self.modified == other.modified
            )
        return False

    @staticmethod
    def from_compose(service_name: str, service: dict) -> "Service":
        image = service.get("image", "")
        image_parts = image.split(":")

        # If no tag is specified, use 'latest' as default
        if len(image_parts) == 1:
            image_parts.append("latest")

        return Service(
            name=service_name,
            image=image_parts[0],
            tag=image_parts[1],
        )


class NewFileContents(BaseModel):
    content: str
    commit_hash: str
    tags: list[str]
    commit_date: datetime
    author: str


def iterate_changed_commits(
    repo_path: str, file_path: str, branch: str
) -> Generator[NewFileContents, None, None]:
    # Initialize a Repo object for the git repository
    repo = Repo(repo_path)

    # Get the specified branch
    selected_branch = repo.heads[branch]

    # Iterate over the commits in the selected branch
    for commit in reversed(
        list(selected_branch.commit.iter_items(repo, selected_branch.path))
    ):
        # Check if the file was changed in this commit
        if any(
            d.a_path == file_path or d.b_path == file_path
            for d in commit.diff(commit.parents or [])
        ):
            # Get the contents of the file at this commit
            blob = commit.tree / file_path
            content = blob.data_stream.read().decode()

            # Get the tags of this commit
            tags = [tag.name for tag in repo.tags if tag.commit == commit]

            # Get the commit date and author
            commit_date = datetime.fromtimestamp(commit.committed_date)
            author = commit.author.name

            # Yield a NewFileContents object
            yield NewFileContents(
                content=content,
                commit_hash=commit.hexsha,
                tags=tags,
                commit_date=commit_date,
                author=author,
            )


class ApplicationIntegration(BaseModel):
    commit_hash: str
    tags: list[str]
    services: list[Service]
    commit_date: datetime
    author: str


def get_app_integration_from_compose(
    commit_hash: str,
    tags: list[str],
    file_contents: str,
    commit_date: datetime,
    author: str,
) -> ApplicationIntegration:
    # Load the YAML file contents
    docker_compose = yaml.safe_load(file_contents)

    # Get the 'services' section
    services_dict = docker_compose.get("services", {})

    # Create a list of Service objects
    services = [
        Service.from_compose(name, details) for name, details in services_dict.items()
    ]

    # Return an ApplicationIntegration object
    return ApplicationIntegration(
        commit_hash=commit_hash,
        tags=tags,
        services=services,
        commit_date=commit_date,
        author=author,
    )


def get_app_integrations_from_git(
    workspace_path: str, compose_path: str, branch: str
) -> Generator[ApplicationIntegration, None, None]:
    prev_services = None
    for new_file_contents in iterate_changed_commits(
        repo_path=workspace_path, file_path=compose_path, branch=branch
    ):
        app_int = get_app_integration_from_compose(
            commit_hash=new_file_contents.commit_hash,
            tags=new_file_contents.tags,
            file_contents=new_file_contents.content,
            commit_date=new_file_contents.commit_date,
            author=new_file_contents.author,
        )

        # If the services have changed compared to the previous commit, mark the modified services
        if prev_services:
            prev_services_by_name = {service.name: service for service in prev_services}
            for new_service in app_int.services:
                if new_service.name in prev_services_by_name:
                    prev_service = prev_services_by_name[new_service.name]
                    if (
                        new_service.image != prev_service.image
                        or new_service.tag != prev_service.tag
                    ):
                        new_service.modified = True
                else:
                    new_service.modified = True
        # If the services have changed compared to the previous commit, print the ApplicationIntegration object
        if prev_services is None or app_int.services != prev_services:
            yield app_int

        # Update the list of services for the previous commit
        prev_services = app_int.services


def main():
    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="Enumerate changes in docker-compose.yml across git history."
    )

    # Add the arguments
    parser.add_argument(
        "workspace_path", help="The path to the working copy of the git repository."
    )
    parser.add_argument("compose_path", help="The path to the docker-compose.yml file.")
    parser.add_argument(
        "--branch",
        help="The branch to track changes in (default: main).",
        default="main",
    )

    # Parse the arguments
    args = parser.parse_args()

    app_ints = get_app_integrations_from_git(
        args.workspace_path, args.compose_path, args.branch
    )

    # Convert the app_ints object to a JSON string and print it
    print(json.dumps([app_int.model_dump() for app_int in app_ints], default=str))


if __name__ == "__main__":
    main()
