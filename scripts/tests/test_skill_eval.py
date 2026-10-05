"""Tests for skill_eval.py: expanding a suite into case directories and collecting a pass."""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import skill_eval

SUITE = {
    "execution": {"max_turns": 40, "allowed_tools": ["Read"]},
    "graders": {"fired": {"type": "tool_used", "tool": "Skill", "arm": "with-only"}},
    "cases": {
        "short": {
            "description": "A case with its own turn limit.",
            "tags": ["x"],
            "execution": {"max_turns": 10},
            "prompt": "Do it.\n",
            "graders": [{"name": "said", "type": "regex", "pattern": "done"}, "fired"],
        }
    },
}


def test_expand_cases_merges_execution_and_shared_graders():
    case = skill_eval.expand_cases(SUITE)["short"]
    assert case["execution"] == {
        "max_turns": 10,
        "allowed_tools": ["Read"],
        "prompt": "Do it.\n",
    }
    assert case["graders"] == [
        {"name": "said", "type": "regex", "pattern": "done"},
        {"name": "fired", "type": "tool_used", "tool": "Skill", "arm": "with-only"},
    ]
    assert case["context"] == {"scaffold_script": "scaffold.sh"}


def test_expand_cases_takes_the_suite_prompt_and_leaves_out_the_patch():
    suite = {
        "execution": {"prompt": "Review it.\n"},
        "cases": {
            "c": {
                "description": "A case with a change.",
                "patch": "diff --git a/x b/x\n",
                "branch": "fix/x",
                "graders": [{"name": "said", "type": "regex", "pattern": "x"}],
            }
        },
    }
    case = skill_eval.expand_cases(suite)["c"]
    assert case["execution"] == {"prompt": "Review it.\n"}
    assert "patch" not in case and "branch" not in case


def test_expand_cases_rejects_an_unknown_grader():
    suite = {**SUITE, "graders": {}}
    with pytest.raises(ValueError, match="no shared grader 'fired'"):
        skill_eval.expand_cases(suite)


def test_expand_writes_cases_and_keeps_results(tmp_path):
    skill = tmp_path / ".agents/skills/demo"
    (skill / "evals/results/old").mkdir(parents=True)
    (skill / "evals/stale").mkdir()
    (skill / "evals.yaml").write_text(yaml.safe_dump(SUITE))
    (tmp_path / "scripts").mkdir()
    (tmp_path / skill_eval.SCAFFOLD).write_text("#!/usr/bin/env bash\n")

    evals = skill_eval.expand(tmp_path, "demo")

    assert sorted(p.name for p in evals.iterdir()) == ["results", "short"]
    case = yaml.safe_load((evals / "short/case.yaml").read_text())
    assert case == skill_eval.expand_cases(SUITE)["short"]
    link = evals / "short/scaffold.sh"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / skill_eval.SCAFFOLD).resolve()


def test_expand_gives_a_case_with_a_patch_its_own_scaffold(tmp_path):
    suite = {
        "cases": {
            "change": {
                "description": "A case with a change on a branch.",
                "prompt": "Review it.\n",
                "patch": "diff --git a/x b/x\n",
                "branch": "fix/x",
                "graders": [{"name": "said", "type": "regex", "pattern": "x"}],
            }
        }
    }
    skill = tmp_path / ".agents/skills/demo"
    skill.mkdir(parents=True)
    (skill / "evals.yaml").write_text(yaml.safe_dump(suite))

    evals = skill_eval.expand(tmp_path, "demo")

    case_dir = evals / "change"
    assert (case_dir / "change.patch").read_text() == "diff --git a/x b/x\n"
    scaffold = case_dir / "scaffold.sh"
    assert not scaffold.is_symlink()
    assert os.access(scaffold, os.X_OK)
    assert scaffold.read_text().splitlines()[-1] == (
        f"exec bash {tmp_path / skill_eval.SCAFFOLD} {case_dir / 'change.patch'} fix/x"
    )


def test_collect_keeps_traces_and_removes_workspaces(tmp_path):
    kept = tmp_path / "claude-eval-x"
    (kept / "out").mkdir(parents=True)
    (kept / "out/trace.jsonl").write_text("{}\n")
    (kept / "sealed").mkdir()
    os.chmod(kept / "sealed", 0)
    results = tmp_path / "results"
    results.mkdir()
    run = {"score": 1, "turns": 4, "tracePath": str(kept / "out/trace.jsonl")}
    (results / "aggregate-result.json").write_text(
        json.dumps(
            {
                "costUsd": 1.234,
                "cases": [
                    {
                        "name": "short",
                        "arms": {
                            "with": [run],
                            "without": [{"score": 0.5, "turns": 3}],
                        },
                    }
                ],
            }
        )
    )

    table = skill_eval.collect(results).splitlines()

    assert (results / "traces/short-with-1.jsonl").read_text() == "{}\n"
    assert not kept.exists()
    assert table[1].split() == ["short", "1.00", "0.50", "4.00", "3.00"]
    assert table[2].split() == ["cost-usd", "1.23"]
