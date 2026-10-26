"""Tests for the recipe scripts in scripts/just/, run against stubbed external commands.

Each test builds a throwaway repo tree, puts fake `uv`, `docker`, `kind`, `helm` and
`just` executables first on PATH, runs the real script there, and checks the calls the
stubs logged: which command, from which directory, with which arguments. That covers the
scripts' own logic without a cluster, a registry or a real test run.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "just"
ROOT = SCRIPTS.parents[1]

# Logs `<name> <cwd> <args>` per call, tab-separated, then runs the per-stub body.
STUB = """#!/usr/bin/env bash
printf '%s\\t%s\\t%s\\n' "$(basename "$0")" "$PWD" "$*" >> "$STUB_LOG"
{body}
"""


class Repo:
    """A throwaway repo root with stubbed commands on PATH."""

    def __init__(self, root: Path):
        self.root = root
        self.bin = root / ".stubs"
        self.bin.mkdir()
        self.log = root / ".stub-log"
        self.log.touch()

    def write(self, path: str, text: str = "") -> Path:
        """Create a file under the root, with its parent directories."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def stub(self, name: str, body: str = "") -> None:
        """Put a fake `name` on PATH that logs its call and then runs `body`."""
        path = self.bin / name
        path.write_text(STUB.format(body=body))
        path.chmod(0o755)

    def run(self, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        """Run scripts/just/<script> from the root."""
        environ = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "STUB_LOG": str(self.log),
            **env,
        }
        environ.pop("GITHUB_ACTIONS", None)
        environ.update(env)
        return subprocess.run(
            [str(SCRIPTS / script), *args],
            cwd=self.root,
            env=environ,
            capture_output=True,
            text=True,
        )

    def calls(self, name: str) -> list[tuple[str, str]]:
        """The (cwd relative to the root, args) of every logged call to `name`."""
        result = []
        for line in self.log.read_text().splitlines():
            command, cwd, args = line.split("\t")
            if command == name:
                rel = os.path.relpath(cwd, self.root)
                result.append((rel, args))
        return result


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    """An empty repo root."""
    return Repo(tmp_path)


# --- test.sh -----------------------------------------------------------------------------


@pytest.fixture
def members(repo: Repo) -> Repo:
    """A workspace with two libs, one service and a member directory left over."""
    for member in ("libs/a", "libs/b", "services/s", "tools/t"):
        repo.write(f"{member}/pyproject.toml")
    (repo.root / "libs/orphan").mkdir()
    # `uv run pytest ...` fails when run from the directory named in $FAIL_IN
    repo.stub("uv", '[ "${FAIL_IN:-}" = "$(basename "$PWD")" ] && exit 1; exit 0')
    return repo


PYTEST = "run pytest -q --durations=10"


def test_no_target_sweeps_every_member_then_the_non_member_suites(members: Repo):
    """Each member runs from its own directory; scripts and deploy run from the root."""
    result = members.run("test.sh")
    assert result.returncode == 0, result.stderr
    assert members.calls("uv") == [
        ("libs/a", PYTEST),
        ("libs/b", PYTEST),
        ("services/s", PYTEST),
        ("tools/t", PYTEST),
        (".", f"{PYTEST} scripts/tests"),
        (".", f"{PYTEST} deploy/tests"),
    ]


@pytest.mark.parametrize("target", ["", "."])
def test_empty_and_dot_mean_everything(members: Repo, target: str):
    """`.` names the repo root, which is no member, so it means the full sweep."""
    members.run("test.sh", target)
    assert len(members.calls("uv")) == 6


def test_tier_sweeps_only_its_members(members: Repo):
    """A bare tier runs each of its members and skips directories without a manifest."""
    members.run("test.sh", "libs//")
    assert members.calls("uv") == [("libs/a", PYTEST), ("libs/b", PYTEST)]


def test_scope_inside_a_member_runs_from_the_member(members: Repo):
    """A path below a member is passed on relative to the member directory."""
    members.run("test.sh", "services/s/tests/unit/")
    assert members.calls("uv") == [("services/s", f"{PYTEST} tests/unit")]


def test_several_targets_run_in_order(members: Repo):
    """Members and non-member paths can be mixed."""
    members.run("test.sh", "tools/t", "scripts/tests")
    assert members.calls("uv") == [
        ("tools/t", PYTEST),
        (".", f"{PYTEST} scripts/tests"),
    ]


@pytest.mark.parametrize("args", [["-k", "login"], ["services/s", "--lf"]])
def test_pytest_options_are_refused_as_targets(members: Repo, args: list[str]):
    """An option is a usage error, not a target run from the root."""
    result = members.run("test.sh", *args)
    assert result.returncode == 2
    assert "is not a target" in result.stderr
    assert members.calls("uv") == []


def test_missing_member_fails_without_running_from_the_root(members: Repo):
    """A typo must not fall back to a tree-wide pytest."""
    result = members.run("test.sh", "libs/nope")
    assert result.returncode == 1
    assert "no such member: libs/nope" in result.stderr
    assert members.calls("uv") == []


def test_a_failing_member_does_not_stop_the_sweep(members: Repo):
    """Like CI's matrix, a red member is reported at the end, after all the others ran."""
    result = members.run("test.sh", "libs", "services", FAIL_IN="a")
    assert result.returncode == 1
    assert "pytest failed in: libs/a" in result.stderr
    assert [cwd for cwd, _ in members.calls("uv")] == ["libs/a", "libs/b", "services/s"]


# --- demo-load.sh ------------------------------------------------------------------------

IMAGE_MEMBERS = """\
import sys
python, frontend = ["ars", "dhfs"], ["data-portal"]
print("\\n".join(frontend if "--kind" in sys.argv else python + frontend))
"""


@pytest.fixture
def images(repo: Repo) -> Repo:
    """Image members ars, dhfs (Python) and data-portal (front end).

    The docker store holds the images listed in $PRESENT; the node lists those in $NODE.
    """
    repo.write("scripts/image_members.py", IMAGE_MEMBERS)
    repo.stub(
        "docker",
        """case "$1 $2" in
    "image inspect") [[ " ${PRESENT:-} " == *" $3 "* ]] ;;
    "exec ghga-control-plane")
        echo "IMAGE TAG ID SIZE"
        for ref in ${NODE:-}; do echo "${ref%:*} ${ref##*:} id 1MB"; done ;;
esac""",
    )
    repo.stub("kind")
    return repo


def _ref(name: str) -> str:
    return f"r.io/ghga/{name}:local"


def test_default_profile_loads_every_member_image(images: Repo):
    """Without a profile every per-member image present is loaded."""
    present = " ".join(_ref(n) for n in ("ars", "dhfs", "data-portal", "platform"))
    result = images.run("demo-load.sh", IMAGE_REGISTRY="r.io/ghga", PRESENT=present)
    assert result.returncode == 0, result.stderr
    loaded = [args.split()[-1] for _, args in images.calls("kind")]
    assert loaded == [_ref("ars"), _ref("dhfs"), _ref("data-portal")]
    assert "loaded 3 image(s)" in result.stdout


def test_mono_profile_loads_the_platform_image_and_the_front_end(images: Repo):
    """The mono profile skips the per-member Python images even when they are built."""
    present = " ".join(_ref(n) for n in ("ars", "dhfs", "data-portal", "platform"))
    images.run("demo-load.sh", "mono", IMAGE_REGISTRY="r.io/ghga", PRESENT=present)
    loaded = [args.split()[-1] for _, args in images.calls("kind")]
    assert loaded == [_ref("data-portal"), _ref("platform")]


def test_reclaim_drops_each_docker_copy_after_loading(images: Repo):
    """reclaim=true removes the docker store's copy of every image it loaded."""
    images.run(
        "demo-load.sh",
        "mono",
        "true",
        IMAGE_REGISTRY="r.io/ghga",
        PRESENT=_ref("platform"),
    )
    assert (".", f"image rm {_ref('platform')}") in images.calls("docker")


def test_images_already_on_the_node_count_as_loaded(images: Repo):
    """A store emptied by an earlier reclaim is not mistaken for "never built"."""
    result = images.run(
        "demo-load.sh",
        "mono",
        IMAGE_REGISTRY="r.io/ghga",
        NODE=f"{_ref('platform')} {_ref('data-portal')}",
    )
    assert result.returncode == 0, result.stderr
    assert "loaded 0 image(s) into the kind node (2 already there)" in result.stdout
    assert images.calls("kind") == []


def test_a_failing_member_listing_fails_the_load(images: Repo):
    """The listing's failure is the error, not an empty set of images."""
    images.write("scripts/image_members.py", "raise SystemExit(3)")
    result = images.run("demo-load.sh", "mono", IMAGE_REGISTRY="r.io/ghga")
    assert result.returncode == 3
    assert images.calls("kind") == []


def test_nothing_built_names_the_build_recipes(images: Repo):
    """No image anywhere is an error that says what to run."""
    result = images.run("demo-load.sh", IMAGE_REGISTRY="r.io/ghga")
    assert result.returncode == 1
    assert "just demo-images" in result.stderr


def test_unknown_profile_is_rejected(images: Repo):
    """Only `mono` or nothing is a profile."""
    result = images.run("demo-load.sh", "mnoo", IMAGE_REGISTRY="r.io/ghga")
    assert result.returncode == 1
    assert "unknown profile 'mnoo'" in result.stderr


# --- install-demo.sh ---------------------------------------------------------------------

CHART = "deploy/charts/ghga-demo"


@pytest.fixture
def chart(repo: Repo) -> Repo:
    """The umbrella chart's values files, with stubbed helm and just."""
    repo.write(f"{CHART}/values-local.yaml")
    repo.write(f"{CHART}/values-mono.yaml")
    repo.stub("helm")
    repo.stub("just", '[ "$1" = _local-image-ids ] && echo "{}"; exit 0')
    return repo


def _values_files(repo: Repo) -> list[str]:
    [(_, args)] = repo.calls("helm")
    words = args.split()
    return [words[i + 1] for i, word in enumerate(words) if word == "-f"]


def test_install_renders_installs_and_waits(chart: Repo):
    """The chart is rendered first, and the install is followed by the readiness wait."""
    result = chart.run("install-demo.sh", "")
    assert result.returncode == 0, result.stderr
    assert [args for _, args in chart.calls("just")] == [
        "demo-template",
        "_local-image-ids",
        "wait-ready",
    ]
    assert _values_files(chart) == [f"{CHART}/values-local.yaml"]


def test_mono_overlay_comes_after_the_values_passed_in(chart: Repo):
    """The mono overlay is last, so it wins over the test-bed values."""
    chart.run("install-demo.sh", "mono", "-f", f"{CHART}/values-testbed.yaml")
    assert _values_files(chart) == [
        f"{CHART}/values-local.yaml",
        f"{CHART}/values-testbed.yaml",
        f"{CHART}/values-mono.yaml",
    ]


def test_missing_mono_overlay_says_to_generate_the_charts(chart: Repo):
    """values-mono.yaml is generated, so its absence points at `just charts`."""
    (chart.root / CHART / "values-mono.yaml").unlink()
    result = chart.run("install-demo.sh", "mono")
    assert result.returncode == 1
    assert "just charts" in result.stderr
    assert chart.calls("helm") == []


def test_unknown_install_profile_is_rejected(chart: Repo):
    """A misspelt profile fails before anything is installed."""
    result = chart.run("install-demo.sh", "mnoo")
    assert result.returncode == 1
    assert chart.calls("helm") == []


# --- pypi-drift.sh -----------------------------------------------------------------------


def _git(repo: Repo, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def branch(repo: Repo) -> Repo:
    """A repo whose `feature` branch changed libs/a/x.py since `base`.

    The stubbed drift script fails with the lines in $DRIFT, and passes without it.
    """
    _git(repo, "init", "-q", "-b", "base")
    repo.write("README.md")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "feature")
    repo.write("libs/a/x.py")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "change")
    repo.stub(
        "uv",
        'cat > "$STUB_LOG.stdin"; [ -z "${DRIFT:-}" ] || { echo "$DRIFT" >&2; exit 1; }',
    )
    return repo


def test_no_drift_passes_and_hands_over_the_changed_files(branch: Repo):
    """The drift script gets the three-dot diff and the merge base."""
    result = branch.run("pypi-drift.sh", "base")
    assert result.returncode == 0, result.stderr
    [(_, args)] = branch.calls("uv")
    assert args.startswith("run -q --script scripts/pypi_drift.py --base ")
    stdin = Path(f"{branch.log}.stdin").read_text()
    assert stdin.splitlines() == ["libs/a/x.py"]


def test_drift_is_reported_as_errors(branch: Repo):
    """Locally every line the script reports becomes an `error:` line."""
    result = branch.run("pypi-drift.sh", "base", DRIFT="libs/a changed")
    assert result.returncode == 1
    assert "error: libs/a changed" in result.stderr


def test_drift_is_annotated_on_github(branch: Repo):
    """On GitHub Actions the lines become `::error::` annotations."""
    result = branch.run(
        "pypi-drift.sh", "base", DRIFT="libs/a changed", GITHUB_ACTIONS="true"
    )
    assert result.returncode == 1
    assert "::error::libs/a changed" in result.stdout


def test_missing_base_fails_instead_of_passing(branch: Repo):
    """An unknown change set is no evidence of no drift."""
    result = branch.run("pypi-drift.sh", "no-such-ref")
    assert result.returncode == 1
    assert "no base commit to compare against (no-such-ref)" in result.stderr
    assert branch.calls("uv") == []


# --- the justfile ------------------------------------------------------------------------

needs_just = pytest.mark.skipif(shutil.which("just") is None, reason="just not on PATH")


@needs_just
def test_every_recipe_script_is_called_and_executable():
    """No script in scripts/just/ is orphaned, and each one can run."""
    justfile = (ROOT / "justfile").read_text()
    for script in SCRIPTS.glob("*.sh"):
        assert f"scripts/just/{script.name}" in justfile or any(
            f"scripts/just/{script.name}" in other.read_text()
            for other in SCRIPTS.glob("*.sh")
        ), f"{script.name} is called by no recipe"
        assert os.access(script, os.X_OK), f"{script.name} is not executable"


@needs_just
def test_every_recipe_parses():
    """`just --dry-run` evaluates each recipe, given a placeholder per required parameter."""
    dump = subprocess.run(
        ["just", "--dump", "--dump-format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    recipes = json.loads(dump)["recipes"]
    assert "test" in recipes
    for name, recipe in recipes.items():
        args = [
            "x"
            for param in recipe["parameters"]
            if param["kind"] == "singular" and param["default"] is None
        ]
        result = subprocess.run(
            ["just", "--dry-run", "--no-deps", name, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (name, result.stderr)


def _just(*args: str, stubs: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}"}
    env["STUB_LOG"] = str(stubs / "log")
    return subprocess.run(
        ["just", *args], cwd=ROOT, env=env, capture_output=True, text=True
    )


@needs_just
@pytest.mark.parametrize(
    "recipe, expected",
    [
        (
            ["image", "frontend/data-portal", "ci", "--build-arg", "X=a b"],
            ["--build-arg", "X=a b", "-t", "docker.io/ghga/data-portal:ci"],
        ),
        (
            ["image", "services/auth-service", "ci", "--pull"],
            ["--pull", "-t", "docker.io/ghga/auth-service:ci", "."],
        ),
        (
            ["image-mono", "ci", "--build-arg", "X=a b"],
            ["--build-arg", "X=a b", "-t", "docker.io/ghga/platform:ci", "."],
        ),
    ],
)
def test_image_recipes_pass_build_flags_through_whole(
    tmp_path: Path, recipe: list[str], expected: list[str]
):
    """A build flag with a space reaches docker as one argument, followed by the tag."""
    stub = tmp_path / "docker"
    stub.write_text('#!/usr/bin/env bash\nprintf \'%s\\n\' "$@" > "$STUB_LOG"\n')
    stub.chmod(0o755)
    result = _just(*recipe, stubs=tmp_path)
    assert result.returncode == 0, result.stderr
    args = (tmp_path / "log").read_text().splitlines()
    assert any(args[i : i + len(expected)] == expected for i in range(len(args))), args
