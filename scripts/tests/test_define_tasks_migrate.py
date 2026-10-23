"""Tests for the define-tasks skill's move of a plan's store to one document per comment."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".agents/skills/define-tasks/scripts/migrate_store.py"


@pytest.fixture
def saved(tmp_path):
    """The files ArtifactData `list` saves for an old plan's comments and picks."""
    source = tmp_path / "saved"
    (source / "comments").mkdir(parents=True)
    (source / "preferences").mkdir()
    owner = {
        "items": {
            "a1": {
                "point": "T1.2",
                "text": "Why?",
                "thread": None,
                "createdAt": "2026-10-08T11:00:00Z",
                "resolved": False,
            },
            "a1-r1": {
                "point": "T1.2",
                "text": "Because.",
                "thread": "a1",
                "byClaude": True,
                "createdAt": "2026-10-08T11:01:00Z",
            },
            "broken": {"text": "no point"},
        }
    }
    wrapped = {"id": "u_owner", "data": owner, "version": 7}
    (source / "comments/u_owner.json").write_text(json.dumps(wrapped))
    (source / "preferences/u_bob.json").write_text(
        json.dumps({"D1": "B", "updatedAt": "2026-10-08T12:00:00Z"})
    )
    return source


def test_moves_comments_and_picks(saved, tmp_path):
    target = tmp_path / "new"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(saved), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    # two comments, one picks document and a people entry for each of the two people
    assert "5 documents to write and 2 to delete, in 1 batches" in result.stdout
    reply = json.loads((target / "data/users/u_owner/c-a1-r1.json").read_text())
    assert reply == {
        "point": "T1.2",
        "text": "Because.",
        "thread": "a1",
        "byClaude": True,
        "createdAt": "2026-10-08T11:01:00Z",
    }
    assert not (target / "data/users/u_owner/c-broken.json").exists()
    assert json.loads((target / "data/users/u_bob/picks.json").read_text())["D1"] == "B"
    listed = json.loads((target / "people/u_owner.json").read_text())
    assert listed == {"listedAt": "2026-10-08T11:00:00Z"}
    (batch,) = json.loads((target / "batches.json").read_text())
    deletes = [write for write in batch if write["op"] == "delete"]
    assert deletes == [
        {
            "op": "delete",
            "collection": "comments",
            "doc_id": "u_owner",
            "if_version": 7,
        },
        {"op": "delete", "collection": "preferences", "doc_id": "u_bob"},
    ]
    assert all(
        Path(write["file_path"]).is_file() for write in batch if write["op"] == "set"
    )
