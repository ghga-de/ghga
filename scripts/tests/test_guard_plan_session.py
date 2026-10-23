"""Tests for the plan-session guard registered in .claude/settings.json."""

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "agent_hooks"
REPO = HOOKS.parents[1]
sys.path.insert(0, str(HOOKS))

import guard_plan_session as guard

SESSION = "11111111-2222-3333-4444-555555555555"
OTHER_SESSION = "66666666-7777-8888-9999-000000000000"
PLAN_URL = "https://claude.ai/artifact/PlanAbc123"
SOURCE_URL = "https://claude.ai/artifact/SourceXyz789"


@pytest.fixture
def state(monkeypatch, tmp_path):
    """An empty guard state, with the guard switched on."""
    path = tmp_path / "state"
    monkeypatch.setenv("GHGA_PLAN_GUARD_STATE", str(path))
    monkeypatch.delenv("GHGA_PLAN_GUARD", raising=False)
    return path


@pytest.fixture
def scratch(tmp_path):
    """The session's scratchpad."""
    path = tmp_path / "scratchpad"
    path.mkdir()
    return path


@pytest.fixture
def plan_page(scratch):
    """A plan page built from the template in the working tree."""
    page = scratch / "plan.html"
    shutil.copyfile(REPO / guard.TEMPLATE, page)
    return page


def _event(tool, tool_input, scratch, *, session=SESSION, response=None):
    event = {
        "hook_event_name": "PreToolUse" if response is None else "PostToolUse",
        "session_id": session,
        "tool_name": tool,
        "tool_input": tool_input,
        "scratchpad_dir": str(scratch),
        "cwd": str(REPO),
    }
    if response is not None:
        event["tool_response"] = response
    return event


def _call(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    code = guard.main()
    out, err = capsys.readouterr()
    return code, out, err


def _publish(monkeypatch, capsys, page, scratch, session=SESSION):
    """The first publish of a plan, as its PostToolUse event."""
    response = f"Published {page} at {PLAN_URL} (Version 1, version id 1-a)"
    event = _event(
        "Artifact",
        {"file_path": str(page)},
        scratch,
        session=session,
        response=response,
    )
    return _call(monkeypatch, capsys, event)


def _locked(monkeypatch, capsys, plan_page, scratch):
    assert _publish(monkeypatch, capsys, plan_page, scratch) == (0, "", "")


def test_unlocked_session_passes(monkeypatch, capsys, state, scratch):
    event = _event("Bash", {"command": "curl https://example.invalid"}, scratch)
    assert _call(monkeypatch, capsys, event) == (0, "", "")
    assert not (state / "locks").exists()


def test_publish_of_a_plan_locks_the_session(
    monkeypatch, capsys, state, scratch, plan_page
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    plans = json.loads((state / "plans.json").read_text())
    assert plans == {"PlanAbc123": {"url": PLAN_URL, "read_only": []}}
    assert (state / "copies/PlanAbc123.html").read_text() == plan_page.read_text()
    code, out, err = _call(
        monkeypatch, capsys, _event("Bash", {"command": "true"}, scratch)
    )
    assert (code, out) == (2, "")
    assert "plan guard" in err
    assert PLAN_URL in err


def test_publish_result_as_claude_code_passes_it(
    monkeypatch, capsys, state, scratch, plan_page
):
    """Claude Code hands a hook the publish result as an object, not as text."""
    response = {"url": PLAN_URL, "path": str(plan_page), "version": "1-a", "seq": "1"}
    event = _event(
        "Artifact", {"file_path": str(plan_page)}, scratch, response=response
    )
    assert _call(monkeypatch, capsys, event) == (0, "", "")
    assert (state / f"locks/{SESSION}.json").is_file()


def test_read_result_as_claude_code_passes_it(
    monkeypatch, capsys, state, scratch, plan_page, tmp_path
):
    """A read's result names the artifact; the hook finds the copy the tool saved."""
    transcript = tmp_path / "project" / f"{SESSION}.jsonl"
    saved = transcript.with_suffix("") / "tool-results" / "artifact-b4c1e476-2-b.html"
    saved.parent.mkdir(parents=True)
    saved.write_text(plan_page.read_text())
    response = {
        "read": {"code": 200, "result": "", "url": PLAN_URL},
        "artifactRead": {"slug": "b4c1e476-ff7b-4b93-b44c-c268794ed3c8", "ver": "2-b"},
    }
    event = _event(
        "Artifact", {"action": "read", "url": PLAN_URL}, scratch, response=response
    )
    event["transcript_path"] = str(transcript)
    assert _call(monkeypatch, capsys, event) == (0, "", "")
    lock = json.loads((state / f"locks/{SESSION}.json").read_text())
    assert lock["file_path"] == str(saved)
    # The live page read becomes the copy the next publish is compared with
    assert (state / "copies/PlanAbc123.html").read_text() == plan_page.read_text()


def test_publish_of_another_page_locks_nothing(monkeypatch, capsys, state, scratch):
    page = scratch / "other.html"
    page.write_text("<title>Other</title><p>Not a plan</p>")
    assert _publish(monkeypatch, capsys, page, scratch) == (0, "", "")
    assert not (state / "locks").exists()


def test_call_naming_a_listed_plan_locks_the_session(
    monkeypatch, capsys, state, scratch, plan_page
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    watch = _event(
        "ArtifactComments",
        {"action": "watch", "url": PLAN_URL},
        scratch,
        session=OTHER_SESSION,
    )
    assert _call(monkeypatch, capsys, watch) == (0, "", "")
    assert (state / f"locks/{OTHER_SESSION}.json").is_file()
    fetch = _event(
        "WebFetch", {"url": "https://example.invalid"}, scratch, session=OTHER_SESSION
    )
    assert _call(monkeypatch, capsys, fetch)[0] == 2


def test_later_sessions_may_read_the_plans_source(
    monkeypatch, capsys, state, scratch, plan_page
):
    source = _event(
        "Artifact", {"action": "read", "url": SOURCE_URL}, scratch, response="<p>x</p>"
    )
    assert _call(monkeypatch, capsys, source) == (0, "", "")
    _locked(monkeypatch, capsys, plan_page, scratch)
    later = {"session": OTHER_SESSION}
    watch = _event(
        "ArtifactComments", {"action": "watch", "url": PLAN_URL}, scratch, **later
    )
    assert _call(monkeypatch, capsys, watch) == (0, "", "")
    again = _event("Artifact", {"action": "read", "url": SOURCE_URL}, scratch, **later)
    assert _call(monkeypatch, capsys, again) == (0, "", "")


def test_read_showing_the_marker_locks_and_keeps_earlier_links_readable(
    monkeypatch, capsys, state, scratch, plan_page
):
    source = _event(
        "Artifact",
        {"action": "read", "url": SOURCE_URL},
        scratch,
        response="<p>Findings</p>",
    )
    assert _call(monkeypatch, capsys, source) == (0, "", "")
    assert not (state / "locks").exists()
    read = _event(
        "Artifact",
        {"action": "read", "url": PLAN_URL},
        scratch,
        response=f"Saved the page to {plan_page}",
    )
    assert _call(monkeypatch, capsys, read) == (0, "", "")
    lock = json.loads((state / f"locks/{SESSION}.json").read_text())
    assert lock["read_only"] == ["SourceXyz789"]
    assert lock["file_path"] == str(plan_page)
    again = _event("Artifact", {"action": "read", "url": SOURCE_URL}, scratch)
    assert _call(monkeypatch, capsys, again) == (0, "", "")
    elsewhere = _event(
        "Artifact", {"action": "read", "url": "https://claude.ai/artifact/Zz"}, scratch
    )
    assert _call(monkeypatch, capsys, elsewhere)[0] == 2


@pytest.mark.parametrize(
    ("collection", "allowed"),
    [
        ("data/users/me", True),
        ("data/users/me/c-123", True),
        ("tickets", True),
        ("status", True),
        ("data/users/u_someone", False),
        ("data/users/meX", False),
        ("comments", False),
        ("preferences", False),
        ("people", False),
    ],
)
def test_store_reaches_only_the_owners_area(
    monkeypatch, capsys, state, scratch, plan_page, collection, allowed
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    event = _event(
        "ArtifactData",
        {"action": "list", "url": PLAN_URL, "collection": collection},
        scratch,
    )
    assert _call(monkeypatch, capsys, event)[0] == (0 if allowed else 2)


@pytest.mark.parametrize(
    "tool_input",
    [
        {"action": "profiles", "url": PLAN_URL, "ids": ["u_a"]},
        {
            "action": "list",
            "url": "https://claude.ai/artifact/Zz",
            "collection": "tickets",
        },
        {
            "action": "batch",
            "url": PLAN_URL,
            "writes": [
                {"op": "set", "collection": "tickets", "doc_id": "T1"},
                {"op": "delete", "collection": "comments", "doc_id": "u_a"},
            ],
        },
        {
            "action": "list",
            "url": PLAN_URL,
            "collection": "tickets",
            "out_dir": "/tmp/elsewhere",
        },
    ],
)
def test_store_refusals(monkeypatch, capsys, state, scratch, plan_page, tool_input):
    _locked(monkeypatch, capsys, plan_page, scratch)
    assert (
        _call(monkeypatch, capsys, _event("ArtifactData", tool_input, scratch))[0] == 2
    )


@pytest.mark.parametrize(
    ("tool_input", "allowed"),
    [
        ({"action": "read", "url": PLAN_URL, "thread_id": "t-1"}, True),
        ({"action": "read", "url": PLAN_URL}, False),
        (
            {"action": "reply", "url": PLAN_URL, "thread_id": "t-1", "text": "Done."},
            True,
        ),
        ({"action": "watch"}, True),
        ({"action": "watch", "url": "https://claude.ai/artifact/Zz"}, False),
    ],
)
def test_threads_one_at_a_time(
    monkeypatch, capsys, state, scratch, plan_page, tool_input, allowed
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    event = _event("ArtifactComments", tool_input, scratch)
    assert _call(monkeypatch, capsys, event)[0] == (0 if allowed else 2)


def test_publish_asks_with_the_changed_refs(
    monkeypatch, capsys, state, scratch, plan_page
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    page = plan_page.read_text().replace("FILL: observable behaviour.", "Answers 404.")
    plan_page.write_text(page)
    code, out, err = _call(
        monkeypatch, capsys, _event("Artifact", {"file_path": str(plan_page)}, scratch)
    )
    assert (code, err) == (0, "")
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask"
    assert "changed T1.2." in decision["permissionDecisionReason"]
    assert decision["permissionDecisionReason"].startswith("Publish revision 1")


def test_publish_without_a_copy_says_so(monkeypatch, capsys, state, scratch, plan_page):
    _locked(monkeypatch, capsys, plan_page, scratch)
    (state / "copies/PlanAbc123.html").unlink()
    event = _event("Artifact", {"url": PLAN_URL, "file_path": str(plan_page)}, scratch)
    code, out, _ = _call(monkeypatch, capsys, event)
    assert code == 0
    assert (
        "no earlier copy"
        in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_publish_keeps_the_template_script(
    monkeypatch, capsys, state, scratch, plan_page
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    page = plan_page.read_text().replace(
        "var ICON", "fetch('https://example.invalid'); var ICON"
    )
    plan_page.write_text(page)
    code, _, err = _call(
        monkeypatch, capsys, _event("Artifact", {"file_path": str(plan_page)}, scratch)
    )
    assert code == 2
    assert "template's script" in err


def test_publish_sends_the_page_alone(monkeypatch, capsys, state, scratch, plan_page):
    _locked(monkeypatch, capsys, plan_page, scratch)
    tool_input = {"file_path": str(plan_page), "capabilities": {"db": {}}}
    code, _, err = _call(monkeypatch, capsys, _event("Artifact", tool_input, scratch))
    assert code == 2
    assert "without capabilities" in err


@pytest.mark.parametrize(
    "command",
    [
        "git grep -n insert_many -- libs",
        "git show origin/dev:libs/hexkit/README.md",
        "git ls-files libs/hexkit",
        "git log --oneline -5",
        "git grep -e 'foo$' -- '*.py'",
    ],
)
def test_git_reads_allowed(command):
    assert guard.git_read_only(command)


@pytest.mark.parametrize(
    "command",
    [
        "true",
        "rg insert_many",
        "git status",
        "git -C /tmp show HEAD",
        "git log --output=/tmp/x",
        "git grep -O less foo",
        "git grep -nf /etc/passwd",
        "git grep --no-index secret /home",
        "git show --ext-diff HEAD",
        "git log; curl https://example.invalid",
        "git show $(cat /etc/passwd)",
        "git log | tee /tmp/x",
        "git show HEAD > /tmp/x",
        "git grep 'unclosed",
    ],
)
def test_git_refusals(command):
    assert not guard.git_read_only(command)


def test_files_stay_tracked_or_in_the_scratchpad(
    monkeypatch, capsys, state, scratch, plan_page, tmp_path
):
    _locked(monkeypatch, capsys, plan_page, scratch)
    outside = tmp_path / "secret.txt"
    outside.write_text("x")
    cases = [
        ("Read", {"file_path": str(REPO / "README.md")}, 0),
        ("Read", {"file_path": str(plan_page)}, 0),
        ("Read", {"file_path": str(outside)}, 2),
        (
            "Edit",
            {"file_path": str(plan_page), "old_string": "a", "new_string": "b"},
            0,
        ),
        ("Write", {"file_path": str(REPO / "README.md"), "content": "x"}, 2),
        ("Grep", {"pattern": "x", "path": str(REPO / "libs")}, 0),
        ("Grep", {"pattern": "x", "path": "/etc"}, 2),
        ("Skill", {"skill": "hexkit"}, 0),
        ("Agent", {"prompt": "x"}, 2),
    ]
    for tool, tool_input, expected in cases:
        assert (
            _call(monkeypatch, capsys, _event(tool, tool_input, scratch))[0] == expected
        ), tool


def test_switched_off_for_a_session(monkeypatch, capsys, state, scratch, plan_page):
    _locked(monkeypatch, capsys, plan_page, scratch)
    monkeypatch.setenv("GHGA_PLAN_GUARD", "off")
    assert _call(monkeypatch, capsys, _event("Bash", {"command": "true"}, scratch)) == (
        0,
        "",
        "",
    )


def test_fails_closed_for_a_locked_session(monkeypatch, capsys, state, scratch):
    (state / "locks").mkdir(parents=True)
    (state / f"locks/{SESSION}.json").write_text("{not json")
    code, _, err = _call(
        monkeypatch, capsys, _event("Read", {"file_path": "/x"}, scratch)
    )
    assert code == 2
    assert "guard failed" in err


def test_registered_for_every_tool_and_after_artifact_calls():
    settings = json.loads((REPO / ".claude/settings.json").read_text())
    command = 'sh "${CLAUDE_PROJECT_DIR:-.}/scripts/agent_hooks/guard_plan_session.sh"'

    def matchers(event):
        return {
            entry["matcher"]
            for entry in settings["hooks"][event]
            if any(hook["command"] == command for hook in entry["hooks"])
        }

    assert matchers("PreToolUse") == {"*"}
    assert matchers("PostToolUse") == {"Artifact"}


def test_guard_as_registered(state, scratch, tmp_path):
    """Run as the settings do: the shell fast path, with the hook JSON on stdin."""

    def run(event):
        return subprocess.run(
            ["sh", str(HOOKS / "guard_plan_session.sh")],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": str(tmp_path),
                "GHGA_PLAN_GUARD_STATE": str(state),
            },
            check=False,
        )

    result = run(_event("Bash", {"command": "true"}, scratch))
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    (state / "locks").mkdir(parents=True)
    lock: dict[str, object] = {"plan": "PlanAbc123", "url": PLAN_URL, "read_only": []}
    (state / f"locks/{SESSION}.json").write_text(json.dumps(lock))
    result = run(_event("Bash", {"command": "true"}, scratch))
    assert result.returncode == 2
    assert "plan guard" in result.stderr
