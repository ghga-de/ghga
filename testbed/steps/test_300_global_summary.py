# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Step definitions for viewing the global summary in the frontend"""

from datetime import UTC, datetime, timezone

from .conftest import Config, HttpClient, Response, scenarios, then, when

scenarios("../features/300_global_summary.feature")


@when("I get the global summary", target_fixture="response")
def get_the_global_summary(config: Config, http: HttpClient) -> Response:
    url = f"{config.metldata_url}/stats"
    return http.get(url)


@then("the summary statistics is as expected")
def check_summary_statistics(response: Response):
    result = response.json()
    assert isinstance(result, dict)
    assert sorted(result) == ["created", "id", "resource_stats"]
    date_created = datetime.fromisoformat(result["created"].replace("Z", "+00:00"))
    date_now = datetime.now(UTC)
    assert abs((date_created - date_now).seconds) < 24 * 60 * 60
    assert result["id"] == "global"
    resource_stats = result["resource_stats"]
    assert resource_stats == {
        "DataAccessCommittee": {"count": 1},
        "Experiment": {"count": 2},
        "IndividualSupportingFile": {
            "count": 1,
            "stats": {"format": [{"count": 1, "value": "JSON"}]},
        },
        "Individual": {"count": 1, "stats": {"sex": [{"count": 1, "value": "MALE"}]}},
        "Analysis": {"count": 2},
        "Dataset": {"count": 2},
        "Sample": {"count": 2, "stats": {"type": [{"count": 2, "value": "CF_DNA"}]}},
        "ExperimentMethod": {
            "count": 1,
            "stats": {"instrument_model": [{"count": 1, "value": "454_GS"}]},
        },
        "Study": {"count": 2},
        "ProcessDataFile": {
            "count": 2,
            "stats": {"format": [{"count": 2, "value": "VCF"}]},
        },
        "ResearchDataFile": {
            "count": 9,
            "stats": {"format": [{"count": 9, "value": "FASTQ"}]},
        },
        "ExperimentMethodSupportingFile": {
            "count": 1,
            "stats": {"format": [{"count": 1, "value": "TXT"}]},
        },
        "EmbeddedDataset": {"count": 2},
        "Publication": {"count": 2},
        "AnalysisMethod": {"count": 1},
        "AnalysisMethodSupportingFile": {
            "count": 1,
            "stats": {"format": [{"count": 1, "value": "TXT"}]},
        },
        "DataAccessPolicy": {"count": 2},
    }
