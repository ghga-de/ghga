"""Shared fixtures for the tests of the repo scripts."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolated_git_config(monkeypatch):
    """Keep the dev's and the runner's git config out of the test repos.

    A global `commit.gpgsign = true` or `core.hooksPath` would otherwise make the
    commits the tests create fail or run hooks. The variables reach every git the
    tests start, directly or through a script, since both inherit os.environ.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
