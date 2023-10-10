# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Step definitions for examining metadata artifacts in the frontend"""

from .conftest import Config, HttpClient, Response, parse, scenarios, then, when

scenarios("../features/21_artifact_info.feature")


@when("I request info on all available artifacts", target_fixture="response")
def request_info_on_artifacts(config: Config, http: HttpClient):
    url = f"{config.metldata_url}/artifacts"
    return http.options(url)


@then("I get the expected info on all the artifacts")
def check_artifacts(response: Response):
    artifact_infos = response.json()
    assert isinstance(artifact_infos, list)
    assert len(artifact_infos) == 5
    artifacts = {artifact["name"]: artifact for artifact in artifact_infos}
    assert sorted(artifacts) == [
        "embedded_public",
        "embedded_restricted",
        "resolved_public",
        "resolved_restricted",
        "stats_public",
    ]
    resolved_public_classes = artifacts["resolved_public"]["resource_classes"]
    assert "Dataset" in resolved_public_classes
    assert "EmbeddedDataset" not in resolved_public_classes
    assert len(resolved_public_classes) == 20
    embedded_public_classes = artifacts["embedded_public"]["resource_classes"]
    assert set(resolved_public_classes).issubset(embedded_public_classes)
    assert "EmbeddedDataset" in embedded_public_classes
    stats_public_classes = artifacts["stats_public"]["resource_classes"]
    assert "DatasetStats" in stats_public_classes


@when(
    parse('I request info on the "{artifact_name}" artifact'), target_fixture="response"
)
def request_info_on_artifact(artifact_name: str, config: Config, http: HttpClient):
    url = f"{config.metldata_url}/artifacts/{artifact_name}"
    return http.options(url)


@then(parse('I get the expected info on the "{artifact_name}" artifact'))
def check_artifact(artifact_name: str, response: Response):
    artifact_info = response.json()
    assert isinstance(artifact_info, dict)
    assert artifact_info["name"] == artifact_name
    classes = artifact_info["resource_classes"]
    num_additional_classes = 1 if artifact_name.startswith("embedded") else 0
    assert len(classes) == 20 + num_additional_classes
