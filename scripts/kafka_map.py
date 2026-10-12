#!/usr/bin/env python3
"""Regenerate the data of the Kafka cascades map from its YAML source.

docs/architecture/kafka-cascades.yaml holds the topology the map draws: the service
names, the reusable sub-cascades, the entrypoint flows and the topic table. This script
validates it and writes it into the marked block of
docs/architecture/kafka-cascade-map.html, then fails when that changed the file, so the
fix is to stage the result. The page's stylesheet and its d3 drawing code are edited by
hand; only the block between the markers is generated.

docs/architecture/kafka-cascade-map.md says where the topology comes from and how to
check it against the code.

Usage:
    uv run python scripts/kafka_map.py
    uv run python scripts/kafka_map.py --check
    uv run python scripts/kafka_map.py --topics
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = "docs/architecture/kafka-cascades.yaml"
PAGE = "docs/architecture/kafka-cascade-map.html"
CHARTS = "deploy/charts"
START = "  // kafka-map-data:start"
END = "  // kafka-map-data:end"
# Every service's retry topic is its own, named after it, so the charts spell it `retry`
# or `retry-` and the map `retry-<service>`; all of them are the one row.
RETRY = re.compile(r"^retry\b.*")

# The publish mechanism of an edge, from the name the source uses to the one the page's
# drawing code switches on. The page labels them plain, outbox, persisted and HTTP.
CLASSES = {"plain": "plain", "outbox": "outbox", "persisted": "persist", "http": "http"}
HTTP_TYPE = "synchronous call"

TOP_FIELDS = ("updated", "services", "fragments", "flows", "topics")
FLOW_FIELDS = ("id", "lane", "actor", "call", "title", "target")
NODE_FIELDS = ("event", "service", "action", "condition", "terminal", "children")
EVENT_FIELDS = ("topic", "type", "class")
TOPIC_FIELDS = ("topic", "class", "types", "producer", "subscribers")
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
# A mapping of up to this many scalar fields is rendered on one line, so an event reads
# as one line while the service names keep one line each.
INLINE_FIELDS = 4


class SourceError(Exception):
    """The YAML source is not a topology this script can render."""


def _fields(
    raw: object, allowed: tuple[str, ...], required: tuple[str, ...], where: str
) -> None:
    """Check one mapping of the source: no unknown field, and every required one set."""
    if not isinstance(raw, dict):
        raise SourceError(f"{where}: must be a mapping")
    unknown = set(raw) - set(allowed)
    if unknown:
        raise SourceError(f"{where}: unknown {', '.join(sorted(unknown))}")
    missing = [field for field in required if not raw.get(field)]
    if missing:
        raise SourceError(f"{where}: lacks {', '.join(missing)}")


def _event(raw: object, where: str) -> dict:
    """Return one edge in the shape the page draws: topic, type and publish class."""
    if isinstance(raw, dict) and "http" in raw:
        if set(raw) != {"http"}:
            raise SourceError(f"{where} event: an http event takes no other field")
        return {"tp": raw["http"], "ty": HTTP_TYPE, "k": CLASSES["http"]}
    _fields(raw, EVENT_FIELDS, EVENT_FIELDS, f"{where} event")
    assert isinstance(raw, dict)
    if raw["class"] not in CLASSES:
        raise SourceError(
            f"{where} event: class {raw['class']!r} is not one of "
            f"{', '.join(sorted(CLASSES))}"
        )
    return {"tp": raw["topic"], "ty": raw["type"], "k": CLASSES[raw["class"]]}


def _substitute(value: object, args: dict[str, str]) -> object:
    """Fill the {{param}} placeholders of a fragment's nodes, at any depth."""
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda match: args[match.group(1)], value)
    if isinstance(value, list):
        return [_substitute(item, args) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, args) for key, item in value.items()}
    return value


def _fragment(raw: object, fragments: dict, where: str) -> list[dict]:
    """Expand one `use` entry into the nodes it stands for."""
    if isinstance(raw, str):
        name, args = raw, {}
    elif isinstance(raw, dict):
        if "fragment" not in raw:
            raise SourceError(f"{where}: use lacks fragment")
        name = raw["fragment"]
        args = {key: item for key, item in raw.items() if key != "fragment"}
    else:
        raise SourceError(f"{where}: use must be a name or a mapping")
    if name not in fragments:
        raise SourceError(f"{where}: no fragment named {name!r}")
    params = set(fragments[name].get("params") or ())
    if set(args) != params:
        expected = ", ".join(sorted(params)) or "no argument"
        raise SourceError(f"{where}: fragment {name!r} takes {expected}")
    nodes = _substitute(fragments[name]["nodes"], args)
    assert isinstance(nodes, list)
    return [_node(node, fragments, f"{where} → {name}") for node in nodes]


def _children(raw: dict, fragments: dict, where: str) -> list[dict]:
    """Return a node's children, with each `use` entry spliced into the list."""
    children: list[dict] = []
    for index, child in enumerate(raw.get("children") or ()):
        spot = f"{where} › {raw['service']}[{index}]"
        if isinstance(child, dict) and "use" in child:
            children += _fragment(child["use"], fragments, spot)
        else:
            children.append(_node(child, fragments, spot))
    return children


def _node(raw: object, fragments: dict, where: str) -> dict:
    """Return one node — a service reacting to an edge — and the nodes below it."""
    if isinstance(raw, dict) and "use" in raw:
        if set(raw) != {"use"}:
            raise SourceError(f"{where}: a use entry takes no other field")
        nodes = _fragment(raw["use"], fragments, where)
        if len(nodes) != 1:
            raise SourceError(
                f"{where}: a fragment of {len(nodes)} nodes stands where one node does"
            )
        return nodes[0]
    _fields(raw, NODE_FIELDS, ("service", "action"), where)
    assert isinstance(raw, dict)
    node: dict = {}
    if "event" in raw:
        node["e"] = _event(raw["event"], where)
    node["s"] = raw["service"]
    node["a"] = raw["action"]
    if raw.get("condition"):
        node["cond"] = raw["condition"]
    if raw.get("terminal"):
        node["term"] = True
    children = _children(raw, fragments, where)
    if children:
        node["kids"] = children
    return node


def _services_used(node: dict, out: set[str]) -> None:
    """Collect every service name a tree names, so each one can be checked."""
    out.add(node["s"])
    for child in node.get("kids") or ():
        _services_used(child, out)


def _flow(raw: object, fragments: dict, index: int) -> dict:
    """Return one entrypoint flow: its label fields and the tree below its root."""
    where = f"flow {index + 1}"
    if isinstance(raw, dict) and raw.get("id"):
        where = f"flow {raw['id']!r}"
    _fields(raw, (*FLOW_FIELDS, "root"), (*FLOW_FIELDS, "root"), where)
    assert isinstance(raw, dict)
    flow = {field: raw[field] for field in FLOW_FIELDS}
    flow["root"] = _node(raw["root"], fragments, where)
    if "e" in flow["root"]:
        raise SourceError(f"{where}: the root is reached by no event")
    return flow


def _topic(raw: object, index: int) -> list:
    """Return one row of the topic table, in the order the page's columns are in."""
    where = f"topic {index + 1}"
    if isinstance(raw, dict) and raw.get("topic"):
        where = f"topic {raw['topic']!r}"
    _fields(raw, TOPIC_FIELDS, ("topic", "class", "types", "producer"), where)
    assert isinstance(raw, dict)
    if raw["class"] not in CLASSES:
        raise SourceError(f"{where}: unknown class {raw['class']!r}")
    return [
        raw["topic"],
        CLASSES[raw["class"]],
        raw["types"],
        raw["producer"],
        raw.get("subscribers"),
    ]


def _check_fragments(fragments: dict) -> None:
    """Check the shape of every fragment, before a flow uses one."""
    for name, fragment in fragments.items():
        _fields(fragment, ("params", "nodes"), ("nodes",), f"fragment {name!r}")


def _check_services(services: dict, flows: list[dict]) -> None:
    """Check that the names the nodes use and the names defined are the same set."""
    used: set[str] = set()
    for flow in flows:
        _services_used(flow["root"], used)
    undefined = used - set(services)
    if undefined:
        raise SourceError(f"services: {', '.join(sorted(undefined))} not defined")
    unused = set(services) - used
    if unused:
        raise SourceError(f"services: {', '.join(sorted(unused))} named by no node")


def build(source: object) -> dict:
    """Validate the YAML source and return the data the page's drawing code reads."""
    _fields(
        source, TOP_FIELDS, ("updated", "services", "flows", "topics"), "the source"
    )
    assert isinstance(source, dict)
    fragments = source.get("fragments") or {}
    _check_fragments(fragments)

    flows = [_flow(flow, fragments, i) for i, flow in enumerate(source["flows"])]
    ids = [flow["id"] for flow in flows]
    duplicate = {flow_id for flow_id in ids if ids.count(flow_id) > 1}
    if duplicate:
        raise SourceError(f"flows: duplicate id {', '.join(sorted(duplicate))}")
    _check_services(source["services"], flows)

    topics = [_topic(topic, i) for i, topic in enumerate(source["topics"])]
    data = {
        "meta": {
            "updated": str(source["updated"]),
            "topics": len(topics),
            "entrypoints": len(flows),
        },
        "services": source["services"],
        "flows": flows,
        "topics": topics,
    }
    left = PLACEHOLDER.search(json.dumps(data, ensure_ascii=False))
    if left:
        raise SourceError(f"a {left.group(0)} placeholder was never filled")
    return data


def _js(value: object, indent: int) -> str:
    """Render a value as JavaScript, one field or element per line where it nests."""
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        scalar = all(not isinstance(item, (dict, list)) for item in value.values())
        if scalar and len(value) <= INLINE_FIELDS:
            inner = ", ".join(
                f"{json.dumps(key, ensure_ascii=False)}: "
                f"{json.dumps(item, ensure_ascii=False)}"
                for key, item in value.items()
            )
            return "{ " + inner + " }"
        lines = [
            f"{pad}  {json.dumps(key, ensure_ascii=False)}: {_js(item, indent + 2)}"
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(lines) + f"\n{pad}}}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value):
            inner = ", ".join(json.dumps(item, ensure_ascii=False) for item in value)
            return "[" + inner + "]"
        lines = [f"{pad}  {_js(item, indent + 2)}" for item in value]
        return "[\n" + ",\n".join(lines) + f"\n{pad}]"
    return json.dumps(value, ensure_ascii=False)


def render(data: dict) -> str:
    """Render the generated block, its markers included."""
    names = {"meta": "META", "services": "SVC", "flows": "FLOWS", "topics": "TOPICS"}
    body = "\n\n".join(
        f"  var {name} = {_js(data[key], 2)};" for key, name in names.items()
    )
    return (
        f"{START}\n"
        f"  // Generated from {SOURCE} by scripts/kafka_map.py.\n"
        f"  // Edit the YAML and run `just kafka-map`; do not edit this block.\n"
        f"{body}\n"
        f"{END}\n"
    )


def update(page: str, block: str) -> str | None:
    """Return the page with the block between the markers replaced, or None if absent."""
    start = page.find(START)
    end = page.find(END)
    if start < 0 or end < 0 or end < start:
        return None
    return page[:start] + block + page[end + len(END) + 1 :]


def chart_topics(root: pathlib.Path) -> dict[str, dict[str, list[str]]]:
    """Return each topic the charts declare, with the charts that write and read it.

    A chart's `_topics` entry carries the topic name and the Kafka ACL the service gets,
    so Write names a producer and Read a subscriber.
    """
    topics: dict[str, dict[str, list[str]]] = {}
    for path in sorted((root / CHARTS).glob("*/values.yaml")):
        values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in (values.get("_topics") or {}).values():
            name = ((entry or {}).get("topic") or {}).get("value")
            # The state-management-service takes `*`, every topic at once. It is a test
            # fixture and the map leaves it out, so it is no topic to compare.
            if not name or name == "*":
                continue
            sides = topics.setdefault(
                RETRY.sub("retry", name), {"Write": [], "Read": []}
            )
            for operation in ((entry.get("kafkaUser") or {}).get("operations")) or ():
                if operation in sides and path.parent.name not in sides[operation]:
                    sides[operation].append(path.parent.name)
    return topics


def report_topics(root: pathlib.Path, topics: list[list]) -> str:
    """Render the charts' topics beside the map's, to be read by a person.

    The ACLs are not an oracle: a chart may grant a service a side it never uses, and
    the map names the service that acts rather than every one entitled to. So this
    lists both and names what only one side has; judging a difference is the reader's.
    """
    charts = chart_topics(root)
    mapped = {RETRY.sub("retry", row[0]): row for row in topics}
    lines = [f"{'topic':<28} {'charts write':<22} charts read"]
    for name in sorted(charts):
        sides = charts[name]
        lines.append(
            f"{name:<28} {','.join(sides['Write']) or '—':<22} "
            f"{','.join(sides['Read']) or '—'}"
        )
    for label, missing in (
        ("in the charts, not in the map", sorted(set(charts) - set(mapped))),
        ("in the map, not in the charts", sorted(set(mapped) - set(charts))),
    ):
        lines += ["", f"{label}: {', '.join(missing) or 'none'}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, root: pathlib.Path = ROOT) -> int:
    """Regenerate the page's data block; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="report a stale page without writing it"
    )
    parser.add_argument(
        "--topics",
        action="store_true",
        help="print the charts' topics beside the map's, and write nothing",
    )
    args = parser.parse_args(argv)

    page_path = root / PAGE
    try:
        source = yaml.safe_load((root / SOURCE).read_text(encoding="utf-8"))
        data = build(source)
        block = render(data)
    except (SourceError, yaml.YAMLError) as error:
        print(f"{SOURCE}: {error}", file=sys.stderr)
        return 1

    if args.topics:
        print(report_topics(root, data["topics"]), end="")
        return 0

    page = page_path.read_text(encoding="utf-8")
    updated = update(page, block)
    if updated is None:
        print(f"{PAGE}: missing {START.strip()} or {END.strip()}", file=sys.stderr)
        return 1
    if updated == page:
        print(f"Kafka map page already matches {pathlib.Path(SOURCE).name}.")
        return 0
    if args.check:
        print(
            f"Kafka map page is behind {pathlib.Path(SOURCE).name}; "
            "run `just kafka-map`.",
            file=sys.stderr,
        )
        return 1
    page_path.write_text(updated, encoding="utf-8")
    # Non-zero on a write, as the other generators here are: the pre-commit hook then
    # fails the commit and the dev stages the page the hook has just rewritten.
    print(
        f"Kafka map page rebuilt from {pathlib.Path(SOURCE).name}; stage {PAGE}.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
