"""Tests for kafka_map.py: the source rules, fragment expansion and the page's block."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kafka_map

ROOT = Path(__file__).resolve().parents[2]

MINIMAL = {
    "updated": "2026-10-09",
    "services": {"RS": "ghga-registry-service", "WPS": "work-package-service"},
    "flows": [
        {
            "id": "box-create",
            "lane": "Upload boxes",
            "actor": "Data Portal · steward",
            "call": "POST /upload-boxes",
            "title": "A data steward creates an upload box",
            "target": "ghga-registry-service",
            "root": {
                "service": "RS",
                "action": "creates the box",
                "children": [
                    {
                        "event": {
                            "topic": "research-data-upload-boxes",
                            "type": "upserted",
                            "class": "outbox",
                        },
                        "service": "WPS",
                        "action": "upserts uploadBoxes",
                        "terminal": True,
                    }
                ],
            },
        }
    ],
    "topics": [
        {
            "topic": "research-data-upload-boxes",
            "class": "outbox",
            "types": "upserted · deleted",
            "producer": "RS",
            "subscribers": "WPS",
        }
    ],
}


def _source(**changes):
    """Return the minimal source, deep enough copied for one change per test."""
    source = yaml.safe_load(yaml.safe_dump(MINIMAL))
    source.update(changes)
    return source


def test_builds_the_minimal_source():
    data = kafka_map.build(_source())
    assert data["meta"] == {"updated": "2026-10-09", "topics": 1, "entrypoints": 1}
    root = data["flows"][0]["root"]
    assert root["s"] == "RS"
    assert root["kids"][0]["e"] == {
        "tp": "research-data-upload-boxes",
        "ty": "upserted",
        "k": "outbox",
    }
    assert root["kids"][0]["term"] is True


def test_counts_come_from_the_source():
    source = _source()
    source["topics"].append(dict(source["topics"][0], topic="studies"))
    assert kafka_map.build(source)["meta"]["topics"] == 2


def test_http_event_needs_no_topic_or_class():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"] = {"http": "UCS · POST /boxes"}
    event = kafka_map.build(source)["flows"][0]["root"]["kids"][0]["e"]
    assert event == {"tp": "UCS · POST /boxes", "ty": "synchronous call", "k": "http"}


def test_persisted_becomes_the_value_the_page_switches_on():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"]["class"] = "persisted"
    assert kafka_map.build(source)["flows"][0]["root"]["kids"][0]["e"]["k"] == "persist"
    assert kafka_map.build(source)["topics"][0][1] == "outbox"


def test_fragment_fills_its_placeholder_at_each_use():
    source = _source()
    source["fragments"] = {
        "box_echo": {
            "params": ["reason"],
            "nodes": [
                {
                    "event": {
                        "topic": "file-upload-boxes",
                        "type": "upserted",
                        "class": "outbox",
                    },
                    "service": "RS",
                    "action": "upserts the box",
                    "condition": "{{reason}}",
                    "terminal": True,
                }
            ],
        }
    }
    children = source["flows"][0]["root"]["children"]
    children.append({"use": {"fragment": "box_echo", "reason": "box created"}})
    kids = kafka_map.build(source)["flows"][0]["root"]["kids"]
    assert kids[1]["cond"] == "box created"


def test_fragment_of_several_nodes_is_spliced_into_the_children():
    source = _source()
    leaf = {
        "event": {
            "topic": "audit-records",
            "type": "audit_record_logged",
            "class": "persisted",
        },
        "service": "WPS",
        "action": "a record",
        "terminal": True,
    }
    source["fragments"] = {"pair": {"nodes": [leaf, dict(leaf, action="another")]}}
    source["flows"][0]["root"]["children"] = [{"use": "pair"}]
    kids = kafka_map.build(source)["flows"][0]["root"]["kids"]
    assert [kid["a"] for kid in kids] == ["a record", "another"]


@pytest.mark.parametrize(
    "message, change",
    [
        ("lacks updated", {"updated": None}),
        ("unknown colours", {"colours": ["red"]}),
    ],
)
def test_rejects_a_bad_top_level(message, change):
    with pytest.raises(kafka_map.SourceError, match=message):
        kafka_map.build(_source(**change))


def test_rejects_an_unknown_node_field():
    source = _source()
    source["flows"][0]["root"]["children"][0]["terminl"] = True
    with pytest.raises(kafka_map.SourceError, match="unknown terminl"):
        kafka_map.build(source)


def test_rejects_a_node_without_an_action():
    source = _source()
    del source["flows"][0]["root"]["children"][0]["action"]
    with pytest.raises(kafka_map.SourceError, match="lacks action"):
        kafka_map.build(source)


def test_rejects_an_unknown_event_class():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"]["class"] = "persistent"
    with pytest.raises(kafka_map.SourceError, match="'persistent' is not one of"):
        kafka_map.build(source)


def test_rejects_a_root_reached_by_an_event():
    source = _source()
    source["flows"][0]["root"]["event"] = {"http": "POST /upload-boxes"}
    with pytest.raises(kafka_map.SourceError, match="reached by no event"):
        kafka_map.build(source)


def test_rejects_a_duplicate_flow_id():
    source = _source()
    source["flows"].append(dict(source["flows"][0]))
    with pytest.raises(kafka_map.SourceError, match="duplicate id box-create"):
        kafka_map.build(source)


def test_rejects_a_service_no_entry_defines():
    source = _source()
    source["flows"][0]["root"]["children"][0]["service"] = "WSP"
    with pytest.raises(kafka_map.SourceError, match="WSP not defined"):
        kafka_map.build(source)


def test_rejects_a_service_no_node_names():
    source = _source()
    source["services"]["DCS"] = "download-controller-service"
    with pytest.raises(kafka_map.SourceError, match="DCS named by no node"):
        kafka_map.build(source)


def test_rejects_a_use_of_an_unknown_fragment():
    source = _source()
    source["flows"][0]["root"]["children"].append({"use": "audit_leaf"})
    with pytest.raises(kafka_map.SourceError, match="no fragment named 'audit_leaf'"):
        kafka_map.build(source)


def test_rejects_a_use_with_the_wrong_argument():
    source = _source()
    source["fragments"] = {
        "box_echo": {
            "params": ["reason"],
            "nodes": [
                {
                    "service": "RS",
                    "action": "upserts the box",
                    "condition": "{{reason}}",
                }
            ],
        }
    }
    source["flows"][0]["root"]["children"].append(
        {"use": {"fragment": "box_echo", "why": "box created"}}
    )
    with pytest.raises(kafka_map.SourceError, match="takes reason"):
        kafka_map.build(source)


def test_rejects_an_unfilled_placeholder():
    source = _source()
    source["flows"][0]["root"]["action"] = "creates {{what}}"
    with pytest.raises(kafka_map.SourceError, match=r"\{\{what\}\} placeholder"):
        kafka_map.build(source)


def test_renders_an_event_on_one_line_and_a_tree_over_many():
    block = kafka_map.render(kafka_map.build(_source()))
    assert (
        '"tp": "research-data-upload-boxes", "ty": "upserted", "k": "outbox"' in block
    )
    assert block.startswith(kafka_map.START)
    assert block.endswith(kafka_map.END + "\n")
    assert "var META = " in block and "var FLOWS = " in block


def test_update_replaces_only_the_marked_block():
    page = f"before\n{kafka_map.START}\n  var SVC = 1;\n{kafka_map.END}\nafter\n"
    updated = kafka_map.update(
        page, f"{kafka_map.START}\n  var SVC = 2;\n{kafka_map.END}\n"
    )
    assert (
        updated
        == f"before\n{kafka_map.START}\n  var SVC = 2;\n{kafka_map.END}\nafter\n"
    )


def test_update_reports_a_page_without_markers():
    assert kafka_map.update("no markers here\n", "block") is None


def test_the_committed_page_matches_the_committed_source():
    """The page's data block is generated, so a hand edit inside it must be caught."""
    assert kafka_map.main(["--check"], root=ROOT) == 0


def _chart(root: Path, name: str, topics: dict) -> None:
    """Write one chart's values.yaml, with just the _topics block the report reads."""
    path = root / "deploy" / "charts" / name
    path.mkdir(parents=True)
    (path / "values.yaml").write_text(yaml.safe_dump({"_topics": topics}))


def test_chart_topics_reads_the_acl_as_the_direction(tmp_path):
    _chart(
        tmp_path,
        "rs",
        {
            "audit": {
                "topic": {"value": "audit-records"},
                "kafkaUser": {"operations": ["Write"]},
            },
            "boxes": {
                "topic": {"value": "file-upload-boxes"},
                "kafkaUser": {"operations": ["Read"]},
            },
        },
    )
    assert kafka_map.chart_topics(tmp_path) == {
        "audit-records": {"Write": ["rs"], "Read": []},
        "file-upload-boxes": {"Write": [], "Read": ["rs"]},
    }


def test_chart_topics_skips_the_wildcard_and_folds_the_retry_topics(tmp_path):
    _chart(
        tmp_path,
        "sms",
        {"wildcard": {"topic": {"value": "*"}, "kafkaUser": {"operations": ["Write"]}}},
    )
    _chart(
        tmp_path,
        "dlqs",
        {
            "retry": {
                "topic": {"value": "retry-"},
                "kafkaUser": {"operations": ["Write"]},
            }
        },
    )
    _chart(
        tmp_path,
        "rs",
        {
            "retry": {
                "topic": {"value": "retry"},
                "kafkaUser": {"operations": ["Read"]},
            }
        },
    )
    assert kafka_map.chart_topics(tmp_path) == {
        "retry": {"Write": ["dlqs"], "Read": ["rs"]}
    }


def test_report_names_a_topic_only_one_side_has(tmp_path):
    _chart(
        tmp_path,
        "rs",
        {"new": {"topic": {"value": "quotas"}, "kafkaUser": {"operations": ["Write"]}}},
    )
    report = kafka_map.report_topics(
        tmp_path, [["studies", "outbox", "upserted", "RS"]]
    )
    assert "in the charts, not in the map: quotas" in report
    assert "in the map, not in the charts: studies" in report


def test_topics_writes_nothing(tmp_path, capsys):
    page = ROOT / kafka_map.PAGE
    before = page.read_text(encoding="utf-8")
    assert kafka_map.main(["--topics"], root=ROOT) == 0
    assert "charts write" in capsys.readouterr().out
    assert page.read_text(encoding="utf-8") == before


def _page(tmp_path: Path, block: str) -> Path:
    """Put a source and a page holding `block` under tmp_path, and return the page."""
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    (tmp_path / kafka_map.SOURCE).write_text(yaml.safe_dump(MINIMAL))
    page = tmp_path / kafka_map.PAGE
    page.write_text(f"<script>\n{block}</script>\n")
    return page


def test_reports_an_up_to_date_page_on_stdout(tmp_path, capsys):
    block = kafka_map.render(kafka_map.build(MINIMAL))
    _page(tmp_path, block)
    assert kafka_map.main([], root=tmp_path) == 0
    assert capsys.readouterr().out == (
        "Kafka map page already matches kafka-cascades.yaml.\n"
    )


def test_reports_the_page_it_rewrote(tmp_path, capsys):
    page = _page(tmp_path, f"{kafka_map.START}\n  var SVC = 1;\n{kafka_map.END}\n")
    assert kafka_map.main([], root=tmp_path) == 1
    assert "Kafka map page rebuilt from kafka-cascades.yaml" in capsys.readouterr().err
    assert "var FLOWS" in page.read_text()


def test_check_reports_a_stale_page_and_writes_nothing(tmp_path, capsys):
    page = _page(tmp_path, f"{kafka_map.START}\n  var SVC = 1;\n{kafka_map.END}\n")
    before = page.read_text()
    assert kafka_map.main(["--check"], root=tmp_path) == 1
    assert "Kafka map page is behind kafka-cascades.yaml" in capsys.readouterr().err
    assert page.read_text() == before
