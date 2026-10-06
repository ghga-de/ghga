#!/usr/bin/env python3
"""Expand a skill's eval suite for `claude plugin eval`, and collect a pass's results.

A suite is one file, .agents/skills/<name>/evals.yaml. The runner wants a directory per
case with its scaffold script inside, so `expand` writes them to the gitignored
.agents/skills/<name>/evals/, each case with a symlink to scripts/skill-eval-scaffold.sh.
A case with a `patch` gets a scaffold of its own instead, which runs the shared one with
the patch and the case's `branch`, so the case starts with that change on that branch,
off an `origin/dev` at the pin.
A run loads only the plugin under test, so a suite that measures a skill next to another
one lists `plugins`, each a set of skills: `expand` then writes a plugin per entry under
evals/, with the cases inside, and the suite runs once per plugin, each against no skill.
`collect` copies each run's trace into the results, removes the run's kept workspace, and
prints the score and turns of each case with and without the skill.

The justfile's `skill-eval` recipe runs both around the runner; see
docs/agent-instructions.md for when a pass is due.

Usage:
    uv run python scripts/skill_eval.py expand adr
    uv run python scripts/skill_eval.py collect .agents/skills/adr/evals/results/<time>
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shlex
import shutil
import stat
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ".agents/skills"
SCAFFOLD = "scripts/skill-eval-scaffold.sh"
SCHEMA_VERSION = "1.1"
DEFAULT_BRANCH = "chore/eval-case"


def expand_cases(suite: dict) -> dict[str, dict]:
    """Return each case of a suite as the runner's case.yaml content, by case name.

    A case's `execution` fields override the suite's, its prompt replaces the suite's
    if it has one, and a grader given by name is replaced with the shared grader of that
    name. A case's `patch` and `branch` stay out: they are for its scaffold.
    """
    shared = suite.get("graders", {})
    cases = {}
    for name, case in suite["cases"].items():
        graders = []
        for grader in case["graders"]:
            if isinstance(grader, str):
                if grader not in shared:
                    raise ValueError(f"case {name}: no shared grader {grader!r}")
                grader = {"name": grader, **shared[grader]}
            graders.append(grader)
        cases[name] = {
            "schema_version": SCHEMA_VERSION,
            "name": name,
            "description": case["description"],
            "tags": case.get("tags", []),
            "context": {"scaffold_script": "scaffold.sh"},
            "execution": {
                **suite.get("execution", {}),
                **case.get("execution", {}),
                **({"prompt": case["prompt"]} if "prompt" in case else {}),
            },
            "graders": graders,
        }
    return cases


def expand(root: pathlib.Path, skill: str) -> list[pathlib.Path]:
    """Write the case directories of a skill's suite, keeping earlier results.

    Return the plugins to run the suite against: the skill's own directory, or one plugin
    per entry of the suite's `plugins`.
    """
    skill_dir = root / SKILLS / skill
    suite = yaml.safe_load((skill_dir / "evals.yaml").read_text(encoding="utf-8"))
    evals = skill_dir / "evals"
    if evals.exists():
        for entry in evals.iterdir():
            if entry.name != "results":
                shutil.rmtree(entry)
    if "plugins" not in suite:
        _write_cases(root, suite, evals)
        return [skill_dir]
    targets = []
    for name, skills in suite["plugins"].items():
        target = evals / name
        (target / ".claude-plugin").mkdir(parents=True)
        manifest = {"name": f"{skill}-{name}", "version": "0.0.0"}
        (target / ".claude-plugin/plugin.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (target / "skills").mkdir()
        for each in skills:
            if not (root / SKILLS / each / "SKILL.md").exists():
                raise ValueError(f"plugin {name}: no skill {each!r}")
            # A copy, not a symlink: a link to the skill whose evals/ holds the plugin is
            # a cycle, which the runner does not follow.
            shutil.copytree(
                root / SKILLS / each,
                target / "skills" / each,
                ignore=shutil.ignore_patterns("evals", "evals.yaml"),
            )
        _write_cases(root, suite, target / "evals")
        targets.append(target)
    return targets


def _write_cases(root: pathlib.Path, suite: dict, evals: pathlib.Path) -> None:
    """Write one directory per case of a suite into evals, with its scaffold."""
    for name, case in expand_cases(suite).items():
        case_dir = evals / name
        case_dir.mkdir(parents=True)
        (case_dir / "case.yaml").write_text(
            yaml.safe_dump(case, sort_keys=False, allow_unicode=True, width=10_000),
            encoding="utf-8",
        )
        patch = suite["cases"][name].get("patch")
        if patch is None:
            (case_dir / "scaffold.sh").symlink_to(
                os.path.relpath(root / SCAFFOLD, case_dir)
            )
            continue
        (case_dir / "change.patch").write_text(patch, encoding="utf-8")
        branch = suite["cases"][name].get("branch", DEFAULT_BRANCH)
        # The runner starts the scaffold from the run's workspace, so the paths are
        # absolute.
        args = [root / SCAFFOLD, case_dir / "change.patch", branch]
        scaffold = case_dir / "scaffold.sh"
        scaffold.write_text(
            "#!/usr/bin/env bash\n# Written by scripts/skill_eval.py.\n"
            f"exec bash {shlex.join(str(arg) for arg in args)}\n",
            encoding="utf-8",
        )
        scaffold.chmod(0o755)


def _mean(values: list[float]) -> str:
    return f"{sum(values) / len(values):.2f}" if values else "-"


def collect(results: pathlib.Path) -> str:
    """Keep each run's trace, remove the kept workspaces and return the score table."""
    result = json.loads((results / "aggregate-result.json").read_text(encoding="utf-8"))
    traces = results / "traces"
    traces.mkdir(exist_ok=True)
    rows = [("case", "with", "without", "turns with", "turns without")]
    for case in result["cases"]:
        arms = case["arms"]
        for arm, runs in arms.items():
            for i, run in enumerate(runs, 1):
                trace = pathlib.Path(run["tracePath"]) if run.get("tracePath") else None
                if trace is None or not trace.exists():
                    continue
                shutil.copyfile(trace, traces / f"{case['name']}-{arm}-{i}.jsonl")
                kept = trace.parent.parent
                # The runner seals what the plugin under test wrote; open it to remove it.
                for path in [kept, *kept.rglob("*")]:
                    if not path.is_symlink():
                        path.chmod(path.stat().st_mode | stat.S_IRWXU)
                shutil.rmtree(kept)
        with_runs, without_runs = arms.get("with", []), arms.get("without", [])
        rows.append(
            (
                case["name"],
                _mean([r["score"] for r in with_runs if r.get("score") is not None]),
                _mean([r["score"] for r in without_runs if r.get("score") is not None]),
                _mean([r["turns"] for r in with_runs if r.get("turns") is not None]),
                _mean([r["turns"] for r in without_runs if r.get("turns") is not None]),
            )
        )
    rows.append(("cost-usd", f"{result.get('costUsd', 0):.2f}", "", "", ""))
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return "\n".join(
        "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=True)
        ).rstrip()
        for row in rows
    )


def main(argv: list[str] | None = None) -> int:
    """Run the subcommand the arguments name."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("expand", help="write a suite's case directories").add_argument(
        "skill"
    )
    sub.add_parser("collect", help="keep the traces, print the scores").add_argument(
        "results", type=pathlib.Path
    )
    args = parser.parse_args(argv)
    if args.command == "expand":
        for target in expand(ROOT, args.skill):
            print(target.relative_to(ROOT))
    else:
        print(collect(args.results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
