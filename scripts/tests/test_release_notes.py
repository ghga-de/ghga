"""Tests for release_notes.py: which pull requests a release lists, and how.

The history mimics the repo's: squash commits on `dev`, a pull request merged with a
merge commit, and a release merge whose pull requests must be listed one by one.
"""

import itertools
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_notes
from release_notes import Entry

SHIPPED = ("libs/demo/src/", "libs/demo/pyproject.toml", "libs/demo/README")

# git orders the log by commit date, and commits made within one second tie.
_seconds = itertools.count(1_700_000_000, 60)


def _git(repo: Path, *args: str) -> str:
    date = f"{next(_seconds)} +0000"
    return subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.org", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
    ).stdout.strip()


def _commit(repo: Path, path: str, message: str, content: str | None = None) -> None:
    """Commits a change to `path`: `content`, or else one more line."""
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        content = file.read_text() + "x\n" if file.exists() else "x\n"
    file.write_text(content)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", message)


def _pyproject(name: str, version: str) -> str:
    return f'[project]\nname = "{name}"\nversion = "{version}"\n'


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with a platform and a library release, and a mixed history between."""
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "libs/demo").mkdir(parents=True)
    (tmp_path / "libs/demo/pyproject.toml").write_text(_pyproject("demo", "1.0.0"))
    _commit(tmp_path, "libs/demo/src/demo.py", "initial")
    _git(tmp_path, "tag", "ghga/1.0.0")
    _git(tmp_path, "tag", "demo/1.0.0")

    _commit(tmp_path, "libs/demo/src/demo.py", "feat(demo): add a thing (#1)")
    _commit(tmp_path, "services/s/app.py", "fix(s): repair the service (#2)")
    _commit(tmp_path, "libs/demo/tests/test_demo.py", "docs: explain the tests (#3)")

    _git(tmp_path, "switch", "-q", "-c", "hotfix/crash")
    _commit(tmp_path, "libs/demo/src/demo.py", "wip")
    _commit(tmp_path, "libs/demo/src/demo.py", "more wip")
    _git(tmp_path, "switch", "-q", "main")
    _git(
        tmp_path,
        "merge", "-q", "--no-ff", "hotfix/crash",
        "-m", "Merge pull request #4 from ghga-de/hotfix/crash",
        "-m", "Fix the crash",
    )  # fmt: skip
    _git(tmp_path, "tag", "ghga/1.1.0-rc.1")

    _git(tmp_path, "switch", "-q", "-c", "dev")
    _commit(
        tmp_path,
        "libs/demo/pyproject.toml",
        "chore(demo): bump the version (#6)",
        _pyproject("demo", "1.1.0"),
    )
    _git(tmp_path, "switch", "-q", "main")
    _git(
        tmp_path,
        "merge", "-q", "--no-ff", "dev",
        "-m", "Merge pull request #5 from ghga-de/dev",
        "-m", "Release 1.1.0",
    )  # fmt: skip

    _commit(
        tmp_path,
        "libs/demo/src/demo.py",
        "feat(demo)!: drop the old API (#7)\n\nBREAKING CHANGE: `old` is gone",
    )

    # Types outside the grammar, as older history and hand-named branches have them.
    _git(tmp_path, "switch", "-q", "-c", "feature/old-style")
    _commit(tmp_path, "services/s/app.py", "Old style")
    _git(tmp_path, "switch", "-q", "main")
    _git(
        tmp_path,
        "merge", "-q", "--no-ff", "feature/old-style",
        "-m", "Merge pull request #8 from ghga-de/feature/old-style",
        "-m", "Add the old style",
    )  # fmt: skip
    _commit(tmp_path, "libs/demo/src/demo.py", "Feature/pypi publish (#9)")

    _git(tmp_path, "tag", "ghga/1.1.0")
    _git(tmp_path, "tag", "demo/1.1.0")
    monkeypatch.setattr(release_notes, "ROOT", tmp_path)
    return tmp_path


def _entry(kind="chore", text="x", pr=None, breaking=False, scope=None):
    return Entry(kind, scope, text, pr, breaking, ())


def test_final_release_compares_with_the_previous_final_release(repo):
    """Candidates in between are skipped, so a final release lists its whole cycle."""
    assert release_notes.previous_tag("ghga/1.1.0") == "ghga/1.0.0"


def test_candidate_compares_with_the_previous_candidate(repo):
    assert release_notes.previous_tag("ghga/1.1.0-rc.2") == "ghga/1.1.0-rc.1"


def test_first_release_has_nothing_to_compare_with(repo):
    assert release_notes.previous_tag("ghga/1.0.0") is None
    assert release_notes.previous_tag("other/1.0.0") is None


def test_history_lists_every_pull_request_once(repo):
    """The merged branch's commits and the release merge are not entries of their own."""
    entries = release_notes.entries("ghga/1.0.0", "ghga/1.1.0")
    assert [e.pr for e in entries] == [1, 2, 3, 4, 6, 7, 8, 9]


def test_merged_pull_request_takes_title_and_kind_from_the_merge(repo):
    """A merge commit's PR title is in its body, and its type in the branch name."""
    merged = release_notes.entries("ghga/1.0.0", "ghga/1.1.0")[3]
    assert (merged.kind, merged.text, merged.pr) == ("fix", "Fix the crash", 4)
    assert merged.files == ("libs/demo/src/demo.py",)


def test_platform_lists_only_services_front_end_and_charts(repo):
    """Libraries and tools are dependencies of the platform, with notes of their own."""
    entries = release_notes.entries("ghga/1.0.0", "ghga/1.1.0")
    selected = release_notes.select(entries, release_notes.PLATFORM_PREFIXES)
    assert [e.pr for e in selected] == [2, 8]


def test_library_lists_only_what_changed_its_shipped_files(repo):
    """Tests and other members do not ship in the wheel, so they are left out."""
    entries = release_notes.entries("demo/1.0.0", "demo/1.1.0")
    selected = release_notes.select(entries, SHIPPED)
    assert [e.pr for e in selected] == [1, 4, 6, 7, 9]


def test_unknown_types_are_listed_as_chores(repo):
    """Neither the merged branch's `feature/` nor the squash's `Feature/` is a type."""
    entries = release_notes.entries("ghga/1.0.0", "ghga/1.1.0")
    unknown = [(e.kind, e.text, e.pr) for e in entries if e.pr in {8, 9}]
    assert unknown == [
        ("chore", "Add the old style", 8),
        ("chore", "Feature/pypi publish", 9),
    ]
    notes = release_notes.render("ghga/1.1.0", "ghga/1.0.0", entries)
    chores = notes.split("### Chores\n\n")[1]
    assert "- Add the old style (#8)\n- Feature/pypi publish (#9)" in chores


@pytest.mark.parametrize(
    ("subject", "body", "expected"),
    [
        (
            "feat(ucs): add endpoints (#9)",
            "",
            ("feat", "ucs", "add endpoints", 9, False),
        ),
        ("fix!: drop a field", "", ("fix", None, "drop a field", None, True)),
        (
            "refactor: tidy",
            "BREAKING CHANGE: x",
            ("refactor", None, "tidy", None, True),
        ),
        ("ci: pin an action (#3)", "", ("chore", None, "pin an action", 3, False)),
        ("Update the lock (#8)", "", ("chore", None, "Update the lock", 8, False)),
        ("note: not a type", "", ("chore", None, "note: not a type", None, False)),
        # Types outside the grammar keep their whole subject as the text.
        (
            "Feat: capital type (#10)",
            "",
            ("chore", None, "Feat: capital type", 10, False),
        ),
        (
            "feature(ucs): long form",
            "",
            ("chore", None, "feature(ucs): long form", None, False),
        ),
        ("fix(ucs) no colon", "", ("chore", None, "fix(ucs) no colon", None, False)),
        ("[adr] Fold ADRs (#206)", "", ("chore", None, "[adr] Fold ADRs", 206, False)),
        (
            "UCS: Allow locking (GSI-2445) (#69)",
            "",
            ("chore", None, "UCS: Allow locking (GSI-2445)", 69, False),
        ),
        ("wip", "", ("chore", None, "wip", None, False)),
    ],
)
def test_subject_parsing(subject, body, expected):
    entry = release_notes._entry(subject, body, [])
    assert (entry.kind, entry.scope, entry.text, entry.pr, entry.breaking) == expected


@pytest.mark.parametrize(
    ("branch", "kind"),
    [
        ("feat/GSI-1-add-x", "feat"),
        ("upload/fix/repair", "fix"),
        ("hotfix/crash", "fix"),
        ("renovate/minio-images", "chore"),
        ("feature/pypi-publish", "chore"),
        ("bugfix/crash", "chore"),
        ("fixes/typo", "chore"),
        ("fix_broken_links", "chore"),
        ("GSI-2596-release-notes", "chore"),
        ("dependabot/pip/requests-2.33.0", "chore"),
    ],
)
def test_branch_kind(branch, kind):
    assert release_notes._branch_kind(branch) == kind


def test_render_leaves_out_empty_headings():
    notes = release_notes.render("demo/1.1.0", "demo/1.0.0", [_entry("feat", pr=1)])
    assert "## New features" in notes
    assert "### Features\n\n- X (#1)" in notes
    for heading in ("## Changes", "## Bug fixes", "### Fixes", "### Chores"):
        assert heading not in notes


def test_render_lists_breaking_changes_first_and_drops_the_own_scope():
    entries = [
        _entry("feat", "add a", 1, scope="demo"),
        _entry("feat", "drop b", 2, breaking=True, scope="other"),
    ]
    notes = release_notes.render("demo/1.1.0", "demo/1.0.0", entries)
    assert "- **Breaking:** **other:** Drop b (#2)\n- Add a (#1)" in notes
    assert "## Changes" in notes  # a breaking change is a change users notice


def test_render_without_previous_release_offers_every_summary():
    notes = release_notes.render("ghga/1.0.0", None, [])
    for heading in ("## New features", "## Changes", "## Bug fixes"):
        assert heading in notes
    assert "No earlier `ghga/` release to compare with." in notes


@pytest.fixture
def companions(repo, monkeypatch):
    """Three companions: `demo` changed, `idle` did not, `fresh` was never released."""
    monkeypatch.setattr(
        release_notes,
        "COMPANIONS",
        {"demo": "libs/demo", "idle": "libs/idle", "fresh": "libs/fresh"},
    )
    monkeypatch.setattr(
        release_notes, "shipped_prefixes", lambda path: (f"{path}/src/",)
    )
    _git(repo, "tag", "--delete", "demo/1.1.0")
    _git(repo, "tag", "idle/1.0.0", "ghga/1.0.0")
    return repo


def test_companions_are_tagged_and_released_with_the_platform(companions):
    """A companion takes the platform version, unless it has nothing to release."""
    releases = release_notes.companion_releases("ghga/1.1.0")
    assert [(tag, created) for tag, _, created in releases] == [
        ("demo/1.1.0", True),
        ("fresh/1.1.0", True),
    ]
    assert "- Add a thing (#1)" in releases[0][1]
    assert "No earlier `fresh/` release" in releases[1][1]
    assert _git(companions, "rev-parse", "demo/1.1.0^{commit}") == _git(
        companions, "rev-parse", "ghga/1.1.0^{commit}"
    )


def test_unchanged_companion_keeps_no_tag(companions):
    release_notes.companion_releases("ghga/1.1.0")
    assert _git(companions, "tag", "--list", "idle/*") == "idle/1.0.0"


def test_existing_companion_tag_is_reused(companions):
    _git(companions, "tag", "demo/1.1.0", "ghga/1.1.0")
    releases = release_notes.companion_releases("ghga/1.1.0")
    assert ("demo/1.1.0", False) in [(tag, created) for tag, _, created in releases]


def test_platform_names_the_libraries_and_tools_that_changed(repo, monkeypatch):
    """Their changes are in their own notes; the platform's give version and link."""
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(release_notes, "COMPANIONS", {"steward-kit": "tools/steward"})
    monkeypatch.setattr(
        release_notes,
        "shipped_prefixes",
        lambda path: (f"{path}/src/", f"{path}/pyproject.toml"),
    )
    for path, name, version in [
        ("libs/idle", "idle", "2.0.0"),
        ("libs/other", "other", "3.0.0"),
        ("tools/steward", "steward_kit", "0.0.0"),
    ]:
        (repo / path).mkdir(parents=True)
        (repo / path / "pyproject.toml").write_text(_pyproject(name, version))
    _commit(repo, "tools/steward/src/kit.py", "chore: add members (#10)")
    _git(repo, "tag", "ghga/1.2.0")

    _commit(repo, "libs/demo/src/demo.py", "fix(demo): no bump yet (#11)")
    _commit(
        repo,
        "libs/other/pyproject.toml",
        "chore: bump (#12)",
        _pyproject("other", "3.1.0"),
    )
    _commit(repo, "tools/steward/src/kit.py", "feat: kit thing (#13)")
    _commit(
        repo,
        "libs/newlib/pyproject.toml",
        "feat: newlib (#14)",
        _pyproject("newlib", "1.0.0"),
    )
    _commit(repo, "services/s/app.py", "fix(s): service only (#15)")
    _git(repo, "tag", "ghga/1.3.0")
    _git(repo, "tag", "other/3.1.0")

    assert release_notes.component_lines("ghga/1.2.0", "ghga/1.3.0") == [
        "- demo 1.1.0 (changed, same version)",
        "- newlib 1.0.0 (new)",
        "- [other 3.1.0](https://github.com/ghga-de/ghga/releases/tag/other/3.1.0)"
        " (was 3.0.0)",
        "- steward-kit 1.3.0",
    ]
    text, _ = release_notes.notes("ghga/1.3.0")
    assert text.index("## Libraries and tools") < text.index("## Pull requests")
    assert "fix(demo)" not in text and "No bump yet" not in text
    assert "Service only (#15)" in text
