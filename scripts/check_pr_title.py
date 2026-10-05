#!/usr/bin/env python3
"""Check a pull request title against the naming grammar in docs/conventions.md.

A title is `[<stack>] <Description> (<ISSUE>)` in a stack and `<Description> (<ISSUE>)`
solo, with the issue key optional. Used by .github/workflows/pr-title.yaml, which only
warns: each problem becomes a workflow annotation and a line in the job summary, and the
exit status is 0 either way, until the team decides to make the check fail.

PRs into `main` (releases and hotfixes) and the branches Renovate and the security scan
own are exempt, since their titles are set by those processes.

Usage:
    python3 scripts/check_pr_title.py --head <branch> --base <branch> -- "<title>"
"""

from __future__ import annotations

import argparse
import os
import re
import sys

GRAMMAR = "[<stack>] <Description> (<ISSUE>) in a stack, <Description> (<ISSUE>) solo"
EXAMPLE = "[upload] Add UCS endpoints (GSI-1234)"
RULES = "docs/conventions.md#names-branches-prs-commits"

EXEMPT_HEADS = ("renovate/", "automated/")
EXEMPT_BASES = ("main",)

STACK = re.compile(r"\[([^\]]*)\]( ?)")
STACK_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
KEY_AT_END = re.compile(r"\s*\([A-Z][A-Z0-9]*-\d+\)$")
KEY = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
# One or two words and a colon before the description: a Conventional Commits type
# (`chore:`, `fix(ucs):`) or a stack name written as a label (`Box version:`).
PREFIX = re.compile(r"^[\w-]+(?: [\w-]+)?(?:\([^)]*\))?!?: ")


def is_exempt(head: str, base: str) -> bool:
    """Return whether a PR from `head` into `base` is exempt from the check."""
    return head.startswith(EXEMPT_HEADS) or base in EXEMPT_BASES


def title_problems(title: str) -> list[str]:
    """Return what is wrong with a PR title, one sentence each; empty if nothing is."""
    problems = []
    rest = title.strip()
    if rest.startswith("["):
        stack = STACK.match(rest)
        if not (stack and STACK_NAME.fullmatch(stack.group(1)) and stack.group(2)):
            problems.append(
                "The stack name goes in square brackets, lowercase kebab-case, "
                "followed by a space."
            )
        rest = rest[stack.end() :] if stack else rest
    if rest.endswith("."):
        problems.append("The title takes no full stop at the end.")
        rest = rest.rstrip(".")
    rest = KEY_AT_END.sub("", rest)
    if KEY.search(rest):
        problems.append("The issue key goes at the end, in parentheses, as (GSI-1234).")
        rest = re.sub(r"\(\s*\)", "", KEY.sub("", rest))
        rest = re.sub(r"\s+", " ", rest).strip()
    if PREFIX.match(rest):
        problems.append(
            "No label before the description: a stack name goes in square brackets, "
            "and the commit type is set when the PR is merged."
        )
        # What separated the label from the description (`Box version: - Add`) goes too.
        rest = PREFIX.sub("", rest).lstrip(" -")
    if not rest:
        problems.append("The title needs a description.")
        return problems
    if not (rest[0].isupper() or rest[0].isdigit() or rest[0] == "`"):
        problems.append("The description starts with a capital letter.")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Print the title's problems as warnings; the exit status is always 0."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--head", default="", help="the PR's head branch")
    parser.add_argument("--base", default="", help="the PR's base branch")
    parser.add_argument("title")
    args = parser.parse_args(argv)

    if is_exempt(args.head, args.base):
        print(f"Exempt: {args.head} into {args.base}.")
        return 0
    problems = title_problems(args.title)
    if not problems:
        print("The PR title follows the grammar.")
        return 0

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for problem in problems:
        print(f"::warning title=PR title::{problem}" if in_actions else problem)
    print(f"Expected {GRAMMAR}, for example: {EXAMPLE}. See {RULES}.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(f"**The PR title breaks the naming grammar:** {args.title}\n\n")
            out.writelines(f"- {problem}\n" for problem in problems)
            out.write(f"\nExpected {GRAMMAR}, for example `{EXAMPLE}` ({RULES}).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
