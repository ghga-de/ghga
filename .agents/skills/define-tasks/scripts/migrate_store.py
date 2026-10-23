"""Move a define-tasks plan's store to one document per comment.

A plan built before the per-comment layout keeps each person's comments in
comments/<id>, under `items`, and their picks in preferences/<id>. This reads those
documents from the files that ArtifactData `list` saves with `out_dir`, and writes one
file per new document, plus batches.json: the ArtifactData batches that write the new
documents and delete the old ones. The batches name files, not text, so the comments
move from file to file and never pass through the session.

Usage: migrate_store.py <out_dir of the list calls> <new directory>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BATCH_SIZE = 50  # the most writes one ArtifactData batch takes
FIELDS = (
    "point",
    "text",
    "thread",
    "createdAt",
    "resolved",
    "resolvedBy",
    "resolvedAt",
    "askedClaude",
    "byClaude",
)


def load(path: Path) -> tuple[dict[str, Any], int | None]:
    """A saved document's body and version, whether or not the file wraps them."""
    raw = json.loads(path.read_text())
    if isinstance(raw.get("data"), dict) and "version" in raw:
        return raw["data"], raw["version"]
    return raw, None


def write(
    root: Path, collection: str, doc_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Write one new document's file, and return the batch entry that sends it."""
    path = root / collection / f"{doc_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2))
    return {
        "op": "set",
        "collection": collection,
        "doc_id": doc_id,
        "file_path": str(path.resolve()),
    }


def migrate(source: Path, target: Path) -> list[dict[str, Any]]:
    """Write the new documents' files and return every write, deletes last."""
    sets, deletes = [], []
    stamps: dict[str, list[str]] = {}
    for path in sorted((source / "comments").glob("*.json")):
        person = path.stem
        body, version = load(path)
        stamps.setdefault(person, [])
        for comment_id, item in (body.get("items") or {}).items():
            if not isinstance(item, dict) or not isinstance(item.get("point"), str):
                continue
            new = {key: item[key] for key in FIELDS if key in item}
            sets.append(write(target, f"data/users/{person}", f"c-{comment_id}", new))
            if item.get("createdAt"):
                stamps[person].append(item["createdAt"])
        deletes.append(("comments", person, version))
    for path in sorted((source / "preferences").glob("*.json")):
        person = path.stem
        body, version = load(path)
        sets.append(write(target, f"data/users/{person}", "picks", body))
        stamps.setdefault(person, [])
        if body.get("updatedAt"):
            stamps[person].append(body["updatedAt"])
        deletes.append(("preferences", person, version))
    for person, times in sorted(stamps.items()):
        sets.append(
            write(target, "people", person, {"listedAt": min(times, default="")})
        )
    removals = []
    for collection, doc_id, version in deletes:
        entry: dict[str, Any] = {
            "op": "delete",
            "collection": collection,
            "doc_id": doc_id,
        }
        if version is not None:
            entry["if_version"] = version
        removals.append(entry)
    return sets + removals


def main() -> int:
    """Write the new documents and batches.json, and say how many there are."""
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    writes = migrate(source, target)
    batches = [writes[i : i + BATCH_SIZE] for i in range(0, len(writes), BATCH_SIZE)]
    (target / "batches.json").write_text(json.dumps(batches, indent=2))
    sets = sum(write["op"] == "set" for write in writes)
    print(
        f"{sets} documents to write and {len(writes) - sets} to delete, in"
        f" {len(batches)} batches: {target / 'batches.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
