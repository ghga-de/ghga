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

"""Step definitions for viewing the global summary in the frontend"""

from datetime import datetime, timezone
from operator import itemgetter

import httpx

from .conftest import TIMEOUT, Config, scenarios, then, when

scenarios("../features/20_global_summary.feature")


@when("I get the global summary", target_fixture="response")
def get_the_global_summary(config: Config) -> httpx.Response:
    url = f"{config.metldata_url}/stats"
    return httpx.get(url, timeout=TIMEOUT)


def sort_stats(resource_stats):
    """Sort all lists in the stats according to their values."""
    # TBD: this is only necessary because the global stats in metldata
    # does not return lists ordered by value - we should change that
    for resource_stat in resource_stats.values():
        stats = resource_stat.get("stats")
        if stats:
            for stat in stats.values():
                stat.sort(key=itemgetter("value"))


@then("the summary statistics is as expected")
def check_summary_statistics(response: httpx.Response):
    result = response.json()
    assert isinstance(result, dict)
    assert sorted(result) == ["created", "id", "resource_stats"]
    date_created = datetime.fromisoformat(result["created"])
    date_now = datetime.now(timezone.utc)
    assert abs((date_created - date_now).seconds) < 24 * 60 * 60
    assert result["id"] == "global"
    resource_stats = result["resource_stats"]
    sort_stats(resource_stats)
    assert resource_stats == {
        "Analysis": {"count": 1},
        "AnalysisProcess": {"count": 9},
        "AnalysisProcessOutputFile": {
            "count": 9,
            "stats": {"format": [{"count": 9, "value": "VCF"}]},
        },
        "Biospecimen": {"count": 2},
        "Condition": {"count": 2},
        "DataAccessCommittee": {"count": 2},
        "DataAccessPolicy": {"count": 4},
        "Dataset": {"count": 6},
        "EmbeddedDataset": {"count": 6},
        "Individual": {
            "count": 3,
            "stats": {
                "sex": [
                    {"count": 1, "value": "FEMALE_SEX_FOR_CLINICAL_USE"},
                    {"count": 2, "value": "MALE_SEX_FOR_CLINICAL_USE"},
                ]
            },
        },
        "LibraryPreparationProtocol": {
            "count": 1,
            "stats": {"type": [{"count": 1, "value": "unknown"}]},
        },
        "Publication": {"count": 2},
        "Sample": {"count": 2},
        "SequencingExperiment": {"count": 1},
        "SequencingProcess": {"count": 9},
        "SequencingProcessFile": {
            "count": 9,
            "stats": {"format": [{"count": 9, "value": "FASTQ"}]},
        },
        "SequencingProtocol": {
            "count": 1,
            "stats": {"type": [{"count": 1, "value": "DNA-seq"}]},
        },
        "Study": {"count": 4},
        "StudyFile": {
            "count": 53,
            "stats": {"format": [{"count": 53, "value": "FASTQ"}]},
        },
        "Trio": {"count": 1},
    }
