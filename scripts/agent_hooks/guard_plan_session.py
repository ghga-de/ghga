"""PreToolUse and PostToolUse hook: lock a session that works on a define-tasks plan.

A define-tasks plan page is shared with teammates, and a refine of it runs in a session
that holds the repository and its tools. So that no comment can steer that session past
the plan, the hook locks the session to the plan:

- It recognises a plan by the marker the template carries, in the page a publish sends
  or a read returns, and lists every plan it recognises.
- The first call that names a listed plan, or the first publish or read that shows the
  marker, locks the session to that plan before the call runs. The lock is kept per
  session id, which every resume keeps; the links read before the lock stay readable.
- A locked session uses the artifact tools on the plan only, and of the plan's store only
  the owner's own area, the ticket cards and the status documents. It reads git-tracked
  files and the scratchpad, searches the repository, runs `git grep`, `git show`,
  `git ls-files` and `git log`, and edits files in its scratchpad. Anything else is
  refused with exit code 2.
- A publish of the plan must keep the template's script, and it asks first, naming the
  refs whose text changed since the last publish.

The state lives in ~/.claude/define-tasks-guard, outside the scratchpad, where a locked
session cannot write. GHGA_PLAN_GUARD=off at launch turns the guard off for a session,
such as one that moves a plan's store to a new layout.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = ".agents/skills/define-tasks/assets/plan-template.html"
# The attribute is the marker; plans built before it carry only the comment
MARKERS = ("data-define-tasks-plan", "Built by the define-tasks skill")
ARTIFACT_URL = re.compile(
    r"https://(?:preview\.)?claude\.ai/(?:code/)?artifact/([A-Za-z0-9-]+)"
)
SAVED_PAGE = re.compile(r"(/[^\s'\"`<>]+\.html)")
SCRIPT = re.compile(r"<script>(.*?)</script>", re.DOTALL)
REVISION = re.compile(r"Revision</dt>\s*<dd>\s*(\d+)")
SESSION_ID = re.compile(r"[A-Za-z0-9-]{1,100}")
PREFIX = "Blocked by the plan guard"

ARTIFACT_TOOLS = frozenset({"Artifact", "ArtifactData", "ArtifactComments"})
# Tools that reach nothing outside the session itself
HARMLESS = frozenset(
    {
        "AskUserQuestion",
        "EnterPlanMode",
        "ExitPlanMode",
        "Skill",
        "TodoWrite",
        "ToolSearch",
    }
)
EDITS = frozenset({"Edit", "MultiEdit", "Write"})
SEARCHES = frozenset({"Glob", "Grep"})
# The store resolves `me` to the session's own user, so no one's id is needed here
STORE_PATHS = ("data/users/me", "tickets", "status")
PUBLISH_OPTIONS = frozenset(
    {
        "asset",
        "asset_ids",
        "capabilities",
        "contract",
        "file_paths",
        "files",
        "force",
        "from_url",
        "overwrite_unread",
        "root",
        "type_url",
    }
)
GIT_READS = frozenset({"grep", "log", "ls-files", "show"})
# Options that write a file, run a program, or read beyond tracked content
GIT_REFUSED = (
    "--ext-diff",
    "--file",
    "--no-index",
    "--open-files-in-pager",
    "--output",
    "--textconv",
    "--untracked",
)
GIT_REFUSED_SHORT = frozenset("Of")
# Chaining, redirection and command substitution; quoting is left to shlex
SHELL_SYNTAX = re.compile(r"[;&|<>`\n]|\$\(")
VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "wbr"}
)

Decision = tuple[str, str]
ALLOW: Decision = ("allow", "")


def state_dir() -> Path:
    """Where the registry of plans, the locks and the page copies live."""
    configured = os.environ.get("GHGA_PLAN_GUARD_STATE")
    return (
        Path(configured) if configured else Path.home() / ".claude/define-tasks-guard"
    )


def read_json(path: Path, default: Any) -> Any:
    """The JSON in the file, or the default when there is no file."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write_file(path: Path, text: str) -> None:
    """Replace the file in one step, so a reader never sees half of it."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as file:
        file.write(text)
    os.replace(tmp, path)


def slug(text: str | None) -> str | None:
    """The artifact id in a claude.ai artifact link, if the text holds one."""
    match = ARTIFACT_URL.search(text or "")
    return match.group(1) if match else None


def marked(page: str) -> bool:
    """Whether the page was built from the define-tasks template."""
    return any(marker in page for marker in MARKERS)


def read_lock(state: Path, session: str) -> dict[str, Any] | None:
    """The plan the session is locked to, or None."""
    if not SESSION_ID.fullmatch(session):
        return None
    return read_json(state / "locks" / f"{session}.json", None)


def lock_session(
    state: Path, session: str, plan: str, url: str, file_path: str | None = None
) -> dict[str, Any]:
    """Lock the session to the plan.

    The links the session read before stay readable, and so do those the plan's first
    session read, such as the findings artifact the plan was built from.
    """
    seen = read_json(state / "seen" / f"{session}.json", [])
    listed = read_json(state / "plans.json", {}).get(plan, {}).get("read_only", [])
    record = {
        "plan": plan,
        "url": url,
        "file_path": file_path,
        "read_only": sorted({*seen, *listed}),
    }
    write_file(state / "locks" / f"{session}.json", json.dumps(record))
    return record


def register(state: Path, plan: str, url: str, read_only: list[str]) -> None:
    """Add the plan, and the links read before it, to the list every call is checked against."""
    plans = read_json(state / "plans.json", {})
    entry = plans.get(plan, {})
    known = sorted({*entry.get("read_only", []), *read_only})
    if entry != {"url": url, "read_only": known}:
        plans[plan] = {"url": url, "read_only": known}
        write_file(state / "plans.json", json.dumps(plans))


def inside(path: str | Path, roots: list[Path]) -> bool:
    """Whether the path is one of the roots or lies below one."""
    if not path:
        return False
    resolved = Path(path).resolve()
    for root in roots:
        top = root.resolve()
        if resolved == top or top in resolved.parents:
            return True
    return False


def tracked(path: str) -> bool:
    """Whether the path is a file git tracks in this repository."""
    if not inside(path, [REPO]):
        return False
    rel = Path(path).resolve().relative_to(REPO.resolve())
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", "--", str(rel)],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def git_read_only(command: str) -> bool:
    """Whether the command is one `git grep|show|ls-files|log` that only reads."""
    if SHELL_SYNTAX.search(command):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    if len(words) < 2 or words[0] != "git" or words[1] not in GIT_READS:
        return False
    for word in words[2:]:
        if word == "--":
            break
        if any(word == opt or word.startswith(opt + "=") for opt in GIT_REFUSED):
            return False
        if re.fullmatch(r"-[A-Za-z0-9]+", word) and GIT_REFUSED_SHORT & set(word[1:]):
            return False
    return True


def script_of(page: str) -> str | None:
    """The page's inline script, with line ends and trailing blanks evened out."""
    match = SCRIPT.search(page)
    if not match:
        return None
    return "\n".join(line.rstrip() for line in match.group(1).strip().splitlines())


def template_scripts() -> set[str]:
    """The template's script in the working tree and in every commit that changed it."""
    pages = []
    with contextlib.suppress(OSError):
        pages.append((REPO / TEMPLATE).read_text())
    log = subprocess.run(
        ["git", "-C", str(REPO), "log", "--format=%H", "--", TEMPLATE],
        capture_output=True,
        text=True,
        check=False,
    )
    for sha in log.stdout.split():
        shown = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{sha}:{TEMPLATE}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if shown.returncode == 0:
            pages.append(shown.stdout)
    return {script for script in map(script_of, pages) if script}


class Points(HTMLParser):
    """The text of every element with a data-point attribute, keyed by its ref."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.texts: dict[str, list[str]] = {}
        self.open: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_TAGS:
            return
        ref = dict(attrs).get("data-point")
        if ref:
            self.texts.setdefault(ref, [])
        self.open.append((tag, ref))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index][0] == tag:
                del self.open[index:]
                return

    def handle_data(self, data: str) -> None:
        for _, ref in self.open:
            if ref:
                self.texts[ref].append(data)


def points(page: str) -> dict[str, str]:
    """Each numbered point's text, with its whitespace evened out."""
    parser = Points()
    parser.feed(page)
    return {
        ref: " ".join("".join(parts).split()) for ref, parts in parser.texts.items()
    }


def natural(ref: str) -> list[Any]:
    """A sort key that puts T1.2 before T1.10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", ref)]


def publish_reason(state: Path, plan: str, page: str) -> str:
    """The question the publish prompt asks: which refs the new revision changes."""
    match = REVISION.search(page)
    head = (
        f"Publish revision {match.group(1)} of the define-tasks plan"
        if match
        else "Publish the define-tasks plan"
    )
    copy = state / "copies" / f"{plan}.html"
    if not copy.exists():
        return (
            f"{head}. The plan guard holds no earlier copy of this plan, so it cannot"
            " list what changed; check the page before you approve."
        )
    old, new = points(copy.read_text()), points(page)
    groups = [
        ("changed", [ref for ref in new if ref in old and new[ref] != old[ref]]),
        ("added", [ref for ref in new if ref not in old]),
        ("removed", [ref for ref in old if ref not in new]),
    ]
    parts = [
        f"{label} {', '.join(sorted(refs, key=natural))}"
        for label, refs in groups
        if refs
    ]
    return f"{head}: {'; '.join(parts) if parts else 'no numbered point changed'}."


def judge_publish(
    tool_input: dict[str, Any], lock: dict[str, Any], state: Path, target: str | None
) -> Decision:
    """A publish must send the plan's page alone, with the template's script."""
    options = sorted(PUBLISH_OPTIONS & tool_input.keys())
    if options:
        return (
            "deny",
            f"A publish of the plan sends the page alone, without {', '.join(options)}.",
        )
    file_path = tool_input.get("file_path") or ""
    own_file = lock.get("file_path") and inside(file_path, [Path(lock["file_path"])])
    if target != lock["plan"] and not (target is None and own_file):
        return ("deny", "It publishes only the plan's own page.")
    try:
        page = Path(file_path).read_text()
    except OSError:
        return ("deny", f"The page {file_path} cannot be read.")
    if script_of(page) not in template_scripts():
        return (
            "deny",
            "A publish of the plan keeps the template's script; this page's script"
            " differs from every committed version of plan-template.html.",
        )
    return ("ask", publish_reason(state, lock["plan"], page))


def in_store(collection: str) -> bool:
    """Whether the collection lies in the part of the store a plan session uses."""
    return any(collection == p or collection.startswith(p + "/") for p in STORE_PATHS)


def judge_data(tool_input: dict[str, Any], scratch: list[Path]) -> Decision:
    """ArtifactData reaches the owner's area, the ticket cards and status only."""
    if tool_input.get("action") == "profiles":
        return ("deny", "ArtifactData profiles returns names other people chose.")
    writes = tool_input.get("writes") or []
    collections = (
        [write.get("collection", "") for write in writes]
        if tool_input.get("action") == "batch"
        else [tool_input.get("collection", "")]
    )
    refused = [collection for collection in collections if not in_store(collection)]
    if refused:
        return (
            "deny",
            "ArtifactData reaches only data/users/me, tickets and status of the plan's"
            f" store, not {', '.join(refused)}.",
        )
    files = [tool_input.get("file_path"), tool_input.get("out_dir")]
    files += [write.get("file_path") for write in writes]
    if any(file and not inside(file, scratch) for file in files):
        return (
            "deny",
            "ArtifactData reads and writes local files only in the scratchpad.",
        )
    return ALLOW


def judge_artifact(
    tool: str,
    tool_input: dict[str, Any],
    lock: dict[str, Any],
    state: Path,
    scratch: list[Path],
) -> Decision:
    """The artifact tools act on the plan only."""
    target = slug(tool_input.get("url"))
    other = ("deny", f"{tool} acts only on the plan, not on {tool_input.get('url')}.")
    if tool == "ArtifactComments":
        action = tool_input.get("action")
        if action == "watch" and target is None:
            return ALLOW  # lists this session's watches
        if target != lock["plan"]:
            return other
        if action == "read" and not tool_input.get("thread_id"):
            return (
                "deny",
                "ArtifactComments reads one thread by its thread_id, so other people's"
                " threads stay out of the session.",
            )
        return ALLOW
    if tool == "ArtifactData":
        return judge_data(tool_input, scratch) if target == lock["plan"] else other
    action = tool_input.get("action") or "publish"
    if action == "read" and target in [lock["plan"], *lock.get("read_only", [])]:
        return ALLOW
    if action in ("list", "open") and target == lock["plan"]:
        return ALLOW
    if action == "publish":
        return judge_publish(tool_input, lock, state, target)
    return ("deny", f"Artifact {action} is not available in a plan session.")


def judge(event: dict[str, Any], lock: dict[str, Any], state: Path) -> Decision:
    """What a locked session may do with this tool call."""
    tool = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}
    scratch = [Path(event["scratchpad_dir"])] if event.get("scratchpad_dir") else []
    if lock.get("file_path"):
        scratch.append(Path(lock["file_path"]))
    if tool in HARMLESS:
        return ALLOW
    if tool in ARTIFACT_TOOLS:
        return judge_artifact(tool, tool_input, lock, state, scratch)
    return judge_local(tool, tool_input, event, scratch)


def judge_local(
    tool: str, tool_input: dict[str, Any], event: dict[str, Any], scratch: list[Path]
) -> Decision:
    """Reads stay in tracked files and the scratchpad, edits in the scratchpad."""
    if tool == "Read":
        path = tool_input.get("file_path") or ""
        if inside(path, scratch) or tracked(path):
            return ALLOW
        return (
            "deny",
            f"Read reaches git-tracked files and the scratchpad, not {path}.",
        )
    if tool in SEARCHES:
        path = tool_input.get("path") or event.get("cwd") or ""
        if inside(path, [REPO, *scratch]):
            return ALLOW
        return ("deny", f"{tool} searches this repository and the scratchpad only.")
    if tool in EDITS:
        path = tool_input.get("file_path") or ""
        if inside(path, scratch):
            return ALLOW
        return ("deny", f"{tool} changes files in the scratchpad only, not {path}.")
    if tool == "Bash":
        if git_read_only(tool_input.get("command") or ""):
            return ALLOW
        return (
            "deny",
            "Bash runs only git grep, git show, git ls-files and git log, one command"
            " at a time, without options that write files or run programs.",
        )
    return ("deny", f"{tool} is not available in a plan session.")


def pre(event: dict[str, Any], state: Path) -> int:
    """Lock the session on its first call to a listed plan, then judge the call."""
    session = event.get("session_id") or ""
    tool_input = event.get("tool_input") or {}
    lock = read_lock(state, session)
    if lock is None:
        target = (
            slug(tool_input.get("url"))
            if event.get("tool_name") in ARTIFACT_TOOLS
            else None
        )
        plans = read_json(state / "plans.json", {})
        if not (target and target in plans and SESSION_ID.fullmatch(session)):
            return 0
        lock = lock_session(state, session, target, plans[target]["url"])
    decision, reason = judge(event, lock, state)
    if decision == "deny":
        print(
            f"{PREFIX}: this session is locked to the define-tasks plan {lock['url']}."
            f" {reason}",
            file=sys.stderr,
        )
        return 2
    if decision == "ask":
        output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
        print(json.dumps({"hookSpecificOutput": output}))
    return 0


def saved_page(response: Any, transcript: str | None) -> str | None:
    """The local copy of the page that an Artifact read saved, if it can be found.

    The read's result gives the artifact's id and version, not the copy's path; the
    tool saves the copy in the session's folder as artifact-<id[:8]>-<version>.html.
    A result given as text names the copy instead.
    """
    if isinstance(response, str):
        for candidate in SAVED_PAGE.findall(response):
            if Path(candidate).is_file():
                return candidate
        return None
    read = response.get("artifactRead") if isinstance(response, dict) else None
    if not isinstance(read, dict) or not read.get("slug") or not transcript:
        return None
    folder = Path(transcript).with_suffix("") / "tool-results"
    prefix = f"artifact-{read['slug'][:8]}-"
    exact = folder / f"{prefix}{read.get('ver')}.html"
    if read.get("ver") and exact.is_file():
        return str(exact)
    copies = sorted(
        folder.glob(f"{prefix}*.html"), key=lambda path: path.stat().st_mtime
    )
    return str(copies[-1]) if copies else None


def published(
    tool_input: dict[str, Any], response: Any
) -> tuple[str, str, str, str] | None:
    """The plan, its link, its local page and the page that a publish sent.

    A publish's result carries the artifact's link and the new version; a result given
    as text says "Published".
    """
    file_path = tool_input.get("file_path")
    if not file_path or tool_input.get("asset"):
        return None
    if isinstance(response, dict):
        link = (response.get("url") or "") if response.get("version") else None
    else:
        link = str(response) if "Published" in str(response) else None
    if link is None:
        return None
    try:
        page = Path(file_path).read_text()
    except OSError:
        return None
    found = ARTIFACT_URL.search(tool_input.get("url") or link)
    if not marked(page) or not found:
        return None
    return found.group(1), found.group(0), str(Path(file_path).resolve()), page


def read_plan(
    tool_input: dict[str, Any],
    response: Any,
    transcript: str | None,
    state: Path,
    session: str,
) -> tuple[str, str, str | None] | None:
    """The plan whose marker a read showed; any other link read stays readable."""
    plan = slug(tool_input.get("url"))
    if not plan or tool_input.get("path") or tool_input.get("paths"):
        return None
    file_path = saved_page(response, transcript)
    text = response if isinstance(response, str) else ""
    if marked(text + (Path(file_path).read_text() if file_path else "")):
        return plan, tool_input["url"], file_path
    seen = read_json(state / "seen" / f"{session}.json", [])
    if plan not in seen:
        write_file(state / "seen" / f"{session}.json", json.dumps([*seen, plan]))
    return None


def remember(
    state: Path,
    session: str,
    plan: str,
    url: str,
    file_path: str | None,
    page: str | None,
) -> None:
    """List the plan, lock the session to it, and keep a copy of a published page."""
    register(state, plan, url, read_json(state / "seen" / f"{session}.json", []))
    lock = read_lock(state, session)
    if lock is None:
        lock = lock_session(state, session, plan, url, file_path)
    elif lock["plan"] == plan and file_path and not lock.get("file_path"):
        lock["file_path"] = file_path
        write_file(state / "locks" / f"{session}.json", json.dumps(lock))
    if lock["plan"] == plan and page is not None:
        write_file(state / "copies" / f"{plan}.html", page)


def post(event: dict[str, Any], state: Path) -> int:
    """Recognise a plan in a publish or a read, and lock the session to it."""
    session = event.get("session_id") or ""
    if event.get("tool_name") != "Artifact" or not SESSION_ID.fullmatch(session):
        return 0
    tool_input = event.get("tool_input") or {}
    response = event.get("tool_response")
    action = tool_input.get("action") or "publish"
    if action == "publish":
        sent = published(tool_input, response)
        if sent:
            remember(state, session, *sent)
    elif action == "read":
        transcript = event.get("transcript_path")
        shown = read_plan(tool_input, response, transcript, state, session)
        if shown:
            # The live page is what the next publish changes, so it becomes the copy
            file_path = shown[2]
            live = Path(file_path).read_text() if file_path else None
            remember(state, session, *shown, live)
    return 0


def main() -> int:
    """Judge the tool call, failing closed for a session that is locked."""
    if os.environ.get("GHGA_PLAN_GUARD") == "off":
        return 0
    event = json.load(sys.stdin)
    state = state_dir()
    session = event.get("session_id") or ""
    try:
        if event.get("hook_event_name") == "PostToolUse":
            return post(event, state)
        return pre(event, state)
    except Exception as error:
        locked = (
            SESSION_ID.fullmatch(session)
            and (state / "locks" / f"{session}.json").exists()
        )
        if not locked:
            return 0
        print(
            f"{PREFIX}: the guard failed ({error!r}), so the call is refused.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
