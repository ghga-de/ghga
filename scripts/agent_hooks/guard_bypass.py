"""PreToolUse hook for Bash: block commands that skip the git hooks.

pre-commit runs the same checks as CI (ADR-0036), so a commit that skips it moves
the failure to the pull request. Blocked: `--no-verify` on a git command, `git
commit -n`, `core.hooksPath` set with `-c`, `--config-env` or `git config`, `SKIP=`
before git, `export SKIP=`, and `pre-commit uninstall`, also inside `bash -c`.
Text that only mentions them, such as `rg -- --no-verify`, passes.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import PurePosixPath

ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
OPERATORS = frozenset(";&|()<>\n")
WRAPPERS = frozenset({"env", "sudo", "time", "command", "nohup", "exec", "xargs"})
SHELLS = frozenset({"bash", "sh", "zsh"})
HOOKS_PATH = "core.hookspath"
# git's global options that take a separate value
GIT_VALUE_OPTIONS = frozenset({"-C", "--git-dir", "--work-tree", "--namespace"})
# options whose value could otherwise be read as a flag, as in `-m -n`
VALUE_OPTIONS = frozenset({"-m", "-F", "-c", "-C", "-t", "--message", "--file"})
# where `git commit -mn` reads "n" as the message, not as --no-verify
SHORT_WITH_VALUE = frozenset("mFcCtSu")
# `<<EOF`, `<<-EOF`, `<<'EOF'` and `<<"EOF"`, not the here-string `<<<`
HEREDOC = re.compile(r"(?<!<)<<-?\s*(?:'(\w+)'|\"(\w+)\"|\\?(\w+))")
# the fallback when the command does not parse as shell
RAW_BYPASS = re.compile(
    r"--no-verify|core\.hookspath|(?:^|[\s;&|(])SKIP=|pre-commit\s+uninstall",
    re.IGNORECASE,
)

MESSAGE = (
    "Blocked: {what} skips the git hooks, which run the same checks as CI."
    " Fix what the hook reports and commit again, or ask the dev."
)


def strip_heredocs(command: str) -> str:
    """The command without its here-document bodies, which are text, not commands.

    A commit message passed through `$(cat <<'EOF' ...)` may name the options this
    hook blocks, and its apostrophes would keep the command from parsing.
    """
    lines: list[str] = []
    pending: list[str] = []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        lines.append(line)
        pending = [next(name for name in m if name) for m in HEREDOC.findall(line)]
    return "\n".join(lines)


def segments(command: str) -> list[list[str]]:
    """The simple commands in a shell command line, as lists of words."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    result: list[list[str]] = [[]]
    for token in lexer:
        if set(token) <= OPERATORS:
            result.append([])
        else:
            result[-1].append(token)
    return [words for words in result if words]


def git_bypass(words: list[str]) -> str | None:
    """What in a git command's arguments skips the hooks, if anything."""
    found, i = global_option_bypass(words)
    if found or i >= len(words):
        return found
    subcommand, args = words[i], words[i + 1 :]
    if subcommand == "config":
        return config_bypass(args)
    return argument_bypass(subcommand, args)


def global_option_bypass(words: list[str]) -> tuple[str | None, int]:
    """What in git's global options skips the hooks, and where the subcommand is."""
    i = 0
    while i < len(words) and words[i].startswith("-"):
        option = words[i]
        if option in ("-c", "--config-env") and i + 1 < len(words):
            if words[i + 1].lower().startswith(HOOKS_PATH + "="):
                return f"`git {option} {words[i + 1]}`", i
            i += 2
        elif option.startswith("--config-env=") and HOOKS_PATH in option.lower():
            return f"`git {option}`", i
        else:
            i += 2 if option in GIT_VALUE_OPTIONS else 1
    return None, i


def argument_bypass(subcommand: str, args: list[str]) -> str | None:
    """What in a git subcommand's arguments skips the hooks, if anything."""
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
        elif arg == "--":
            break
        elif arg == "--no-verify":
            return f"`git {subcommand} --no-verify`"
        elif arg in VALUE_OPTIONS:
            skip_next = True
        elif subcommand == "commit" and commit_no_verify(arg):
            return "`git commit -n`"
    return None


def commit_no_verify(arg: str) -> bool:
    """Whether a cluster of short `git commit` options holds -n, as in `-an`."""
    if not re.fullmatch(r"-[A-Za-z]+", arg):
        return False
    for letter in arg[1:]:
        if letter == "n":
            return True
        if letter in SHORT_WITH_VALUE:
            return False
    return False


def config_bypass(args: list[str]) -> str | None:
    """Whether `git config` sets core.hooksPath; reading or unsetting it passes."""
    words = [arg for arg in args if not arg.startswith("-")]
    if words[:1] == ["set"]:
        words = words[1:]
    keys = [word.lower() for word in words]
    if HOOKS_PATH in keys and keys.index(HOOKS_PATH) + 1 < len(keys):
        return "setting core.hooksPath"
    return None


def bypass(command: str) -> str | None:
    """What in the shell command skips the git hooks, or None."""
    command = strip_heredocs(command)
    try:
        commands = segments(command)
    except ValueError:  # unbalanced quotes: fall back to the plain text
        match = RAW_BYPASS.search(command)
        return f"`{match.group().strip(' ;&|(')}`" if match else None
    for words in commands:
        found = segment_bypass(words)
        if found:
            return found
    return None


def without_prefix(words: list[str]) -> tuple[set[str], list[str]]:
    """The variables a simple command assigns, and its words without them and wrappers.

    `SKIP=x git commit` and `env SKIP=x sudo git commit` both come out as `git commit`.
    """
    assigned: set[str] = set()
    while words and (ASSIGNMENT.match(words[0]) or words[0] in WRAPPERS):
        if ASSIGNMENT.match(words[0]):
            assigned.add(words[0].split("=", 1)[0])
        words = words[1:]
        while words and words[0].startswith("-"):
            words = words[1:]
    return assigned, words


def nested_bypass(program: str, args: list[str]) -> str | None:
    """What skips the git hooks in the command a shell or `eval` runs."""
    if program == "eval":
        return bypass(" ".join(args))
    for i, arg in enumerate(args[:-1]):
        if re.fullmatch(r"-[a-z]*c[a-z]*", arg):
            return bypass(args[i + 1])
    return None


def segment_bypass(words: list[str]) -> str | None:
    """What in one simple command skips the git hooks, or None."""
    assigned, words = without_prefix(words)
    if not words:
        return None
    program, args = PurePosixPath(words[0]).name, words[1:]
    if program == "export" and any(arg.startswith("SKIP=") for arg in args):
        return "`export SKIP=`"
    if program in SHELLS or program == "eval":
        return nested_bypass(program, args)
    if program == "uv" and args[:1] == ["run"]:
        args = [arg for arg in args[1:] if not arg.startswith("-")]
        program, args = (args[0], args[1:]) if args else ("", [])
    if program == "pre-commit" and args[:1] == ["uninstall"]:
        return "`pre-commit uninstall`"
    if program == "git":
        if "SKIP" in assigned:
            return "`SKIP=` before git"
        return git_bypass(args)
    return None


def main() -> int:
    """Exit 2 when the Bash command skips the git hooks."""
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    found = bypass(command)
    if found:
        print(MESSAGE.format(what=found), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
