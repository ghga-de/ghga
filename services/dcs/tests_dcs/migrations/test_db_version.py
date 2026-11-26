# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test that the CLI runs a command only on a database at `DB_VERSION`."""

import pytest
from typer.main import get_group
from typer.testing import CliRunner

from dcs import cli as cli_module
from dcs import main
from hexkit.providers.mongodb.migrations import DbVersionMismatchError
from hexkit.providers.mongodb.testutils import MongoDbFixture
from tests_dcs.fixtures.config import get_config

cli = cli_module.cli

# `migrate-db` alone runs on any version, since setting the version is its job
COMMANDS = sorted(set(get_group(cli).commands) - {"migrate-db"})


@pytest.fixture(autouse=True)
def empty_database(mongodb: MongoDbFixture, monkeypatch: pytest.MonkeyPatch):
    """Point the CLI at an empty database, as a fresh deployment finds it."""
    mongodb.empty_collections()
    config = get_config(sources=[mongodb.config])
    monkeypatch.setattr(cli_module, "Config", lambda: config)
    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", lambda config: None)


def stub_command(name: str, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace a command with a stub that records its calls, so it does no real work."""
    calls: list[str] = []
    info = next(info for info in cli.registered_commands if info.name == name)
    monkeypatch.setattr(info, "callback", lambda: calls.append(name))
    return calls


@pytest.mark.parametrize("command", COMMANDS)
def test_command_refuses_unmigrated_db(command: str, monkeypatch: pytest.MonkeyPatch):
    """A command does not start when the database is not migrated."""
    calls = stub_command(command, monkeypatch)
    result = CliRunner().invoke(cli, [command])
    assert isinstance(result.exception, DbVersionMismatchError)
    assert not calls


@pytest.mark.parametrize("command", COMMANDS)
def test_command_runs_after_migrate_db(command: str, monkeypatch: pytest.MonkeyPatch):
    """A command starts once `migrate-db` has brought the database to `DB_VERSION`."""
    result = CliRunner().invoke(cli, ["migrate-db"])
    assert result.exit_code == 0, result.output
    calls = stub_command(command, monkeypatch)
    result = CliRunner().invoke(cli, [command])
    assert result.exit_code == 0, result.output
    assert calls == [command]
