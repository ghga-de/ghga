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


def _extra_topic(source: dict, topic: str, cls: str = "outbox") -> None:
    """Add a topic row and an edge naming it, so the two sides stay consistent."""
    source["topics"].append(
        {"topic": topic, "class": cls, "types": "upserted", "producer": "RS"}
    )
    source["flows"][0]["root"]["children"].append(
        {
            "event": {"topic": topic, "type": "upserted", "class": cls},
            "service": "WPS",
            "action": "reacts",
            "terminal": True,
        }
    )


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
    _extra_topic(source, "studies")
    assert kafka_map.build(source)["meta"]["topics"] == 2


def test_http_event_needs_no_topic_or_class():
    source = _source()
    source["flows"][0]["root"]["children"].append(
        {
            "event": {"http": "UCS · POST /boxes"},
            "service": "WPS",
            "action": "creates the box",
            "terminal": True,
        }
    )
    event = kafka_map.build(source)["flows"][0]["root"]["kids"][1]["e"]
    assert event == {"tp": "UCS · POST /boxes", "ty": "synchronous call", "k": "http"}


def test_persisted_becomes_the_value_the_page_switches_on():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"]["class"] = "persisted"
    source["topics"][0]["class"] = "persisted"
    data = kafka_map.build(source)
    assert data["flows"][0]["root"]["kids"][0]["e"]["k"] == "persist"
    assert data["topics"][0][1] == "persist"


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
    source["topics"].append(
        {
            "topic": "file-upload-boxes",
            "class": "outbox",
            "types": "upserted",
            "producer": "UCS",
        }
    )
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
    source["topics"] = [
        {
            "topic": "audit-records",
            "class": "persisted",
            "types": "audit_record_logged",
            "producer": "RS",
        }
    ]
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


def test_rejects_a_name_neither_service_nor_label():
    source = _source()
    source["flows"][0]["root"]["children"][0]["service"] = "WSP"
    with pytest.raises(kafka_map.SourceError, match="WSP is neither a service nor"):
        kafka_map.build(source)


def test_a_label_names_a_node_the_way_a_service_does():
    source = _source()
    source["labels"] = {"—": "published, nothing subscribes"}
    source["flows"][0]["root"]["children"][0]["service"] = "—"
    del source["services"]["WPS"]
    data = kafka_map.build(source)
    assert data["flows"][0]["root"]["kids"][0]["s"] == "—"
    # the page looks both up in one map
    assert data["services"]["—"] == "published, nothing subscribes"
    assert data["services"]["RS"] == "ghga-registry-service"


def test_rejects_a_label_that_is_also_a_service():
    source = _source()
    source["labels"] = {"WPS": "work-package-service"}
    with pytest.raises(kafka_map.SourceError, match="WPS is also a service"):
        kafka_map.build(source)


def test_rejects_a_label_no_node_names():
    source = _source()
    source["labels"] = {"—": "published, nothing subscribes"}
    with pytest.raises(kafka_map.SourceError, match="— named by no node"):
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


def test_topics_writes_nothing(capsys):
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


def test_rejects_a_topic_an_edge_names_but_the_table_lacks():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"]["topic"] = "studies"
    with pytest.raises(kafka_map.SourceError, match="studies in a flow but not listed"):
        kafka_map.build(source)


def test_rejects_a_topic_row_no_edge_names():
    source = _source()
    source["topics"].append(
        {"topic": "studies", "class": "outbox", "types": "upserted", "producer": "RS"}
    )
    with pytest.raises(kafka_map.SourceError, match="studies listed but in no flow"):
        kafka_map.build(source)


def test_rejects_a_class_the_table_and_the_edge_disagree_on():
    source = _source()
    source["flows"][0]["root"]["children"][0]["event"]["class"] = "persisted"
    with pytest.raises(
        kafka_map.SourceError, match="is outbox in the table but persist"
    ):
        kafka_map.build(source)


def test_rejects_a_topic_listed_twice():
    source = _source()
    source["topics"].append(dict(source["topics"][0]))
    with pytest.raises(kafka_map.SourceError, match="is listed twice"):
        kafka_map.build(source)


def test_a_topic_in_angle_brackets_stands_for_a_set_and_matches_no_row():
    """The replay flow names `<that service's topics>`, which is no single topic."""
    source = _source()
    source["flows"][0]["root"]["children"].append(
        {
            "event": {
                "topic": "&lt;that service's topics&gt;",
                "type": "upserted",
                "class": "outbox",
            },
            "service": "WPS",
            "action": "reacts",
            "terminal": True,
        }
    )
    assert kafka_map.build(source)["meta"]["topics"] == 1


def test_the_retry_rows_fold_into_one_topic():
    source = _source()
    source["topics"].append(
        {
            "topic": "retry-&lt;service&gt;",
            "class": "plain",
            "types": "(the original type)",
            "producer": "DLQS",
        }
    )
    source["flows"][0]["root"]["children"].append(
        {
            "event": {"topic": "retry-ucs", "type": "upserted", "class": "plain"},
            "service": "WPS",
            "action": "reacts",
            "terminal": True,
        }
    )
    assert kafka_map.build(source)["meta"]["topics"] == 2


def test_rejects_a_placeholder_the_fragment_does_not_declare():
    """A stray {{name}} must name its fragment, not raise a KeyError."""
    source = _source()
    source["fragments"] = {
        "box_echo": {
            "params": ["reason"],
            "nodes": [
                {"service": "RS", "action": "upserts {{nope}}", "terminal": True}
            ],
        }
    }
    source["flows"][0]["root"]["children"].append(
        {"use": {"fragment": "box_echo", "reason": "box created"}}
    )
    with pytest.raises(kafka_map.SourceError, match=r"box_echo': \{\{nope\}\} is not"):
        kafka_map.build(source)


def test_rejects_a_field_beside_a_use_in_a_children_list():
    """The field would be dropped, so a typo there must fail rather than vanish."""
    source = _source()
    source["fragments"] = {
        "audit_leaf": {
            "nodes": [{"service": "WPS", "action": "a record", "terminal": True}]
        }
    }
    source["flows"][0]["root"]["children"].append(
        {"use": "audit_leaf", "service": "TYPO"}
    )
    with pytest.raises(kafka_map.SourceError, match="a use entry takes no other field"):
        kafka_map.build(source)
