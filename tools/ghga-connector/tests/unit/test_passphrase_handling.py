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
#

"""Test that private key passphrases are never taken from the command line"""

import inspect
import os
from collections.abc import Callable
from getpass import fallback_getpass
from pathlib import Path

import crypt4gh.keys
import crypt4gh.lib
import pytest
from typer.testing import CliRunner

from ghga_connector import exceptions
from ghga_connector.cli import cli
from ghga_connector.constants import PASSPHRASE_ENV_VAR
from ghga_connector.core.crypt import Crypt4GHDecryptor
from ghga_connector.core.main import (
    async_batch_upload,
    async_download,
    async_ubox,
    get_decryptor,
    upload_files,
)
from ghga_connector.core.utils import get_private_key, prompt_for_passphrase

KEY_DIR = Path(__file__).parent.parent / "fixtures" / "keypair"
ENCRYPTED_KEY = KEY_DIR / "encrypted_key.sec"
ENCRYPTED_KEY_PASSPHRASE = "test"
UNENCRYPTED_KEY = KEY_DIR / "key.sec"
COMMANDS = ("batch-upload", "ubox", "download", "decrypt")


@pytest.fixture(autouse=True)
def no_passphrase_in_environment(monkeypatch):
    """Keep the passphrase of whoever runs the tests out of them"""
    monkeypatch.delenv(PASSPHRASE_ENV_VAR, raising=False)


@pytest.fixture
def prompts(monkeypatch) -> list[str]:
    """Record passphrase prompts instead of asking the user, returning the passphrase
    of the encrypted test key.
    """
    return patch_prompt(monkeypatch, lambda: ENCRYPTED_KEY_PASSPHRASE)


def patch_prompt(monkeypatch, answer: Callable[[], str]) -> list[str]:
    """Replace the passphrase prompt and return the list recording its invocations"""
    recorded: list[str] = []

    def fake_prompt() -> str:
        recorded.append("prompted")
        return answer()

    monkeypatch.setattr("ghga_connector.core.utils.prompt_for_passphrase", fake_prompt)
    return recorded


def encrypt_files(target_dir: Path, count: int) -> dict[str, bytes]:
    """Put `count` Crypt4GH encrypted files into `target_dir`, return their contents"""
    private_key = crypt4gh.keys.get_private_key(
        ENCRYPTED_KEY, callback=lambda: ENCRYPTED_KEY_PASSPHRASE
    )
    public_key = crypt4gh.keys.get_public_key(KEY_DIR / "encrypted_key.pub")
    contents = {}
    for number in range(count):
        content = os.urandom(128)
        contents[f"file{number}"] = content
        plain_file = target_dir / f"file{number}"
        plain_file.write_bytes(content)
        with (
            plain_file.open("rb") as infile,
            (target_dir / f"file{number}.c4gh").open("wb") as outfile,
        ):
            crypt4gh.lib.encrypt(
                keys=[(0, private_key, public_key)], infile=infile, outfile=outfile
            )
        plain_file.unlink()
    return contents


@pytest.mark.parametrize("command", COMMANDS)
def test_passphrase_option_not_exposed(command: str):
    """The passphrase must not be passable as an option, as that would leak it into
    the command line history.
    """
    result = CliRunner().invoke(cli, [command, "--help"])

    assert result.exit_code == 0
    # make sure the help was actually rendered, so this cannot pass vacuously
    assert "--my-private-key-path" in result.output
    assert "--passphrase" not in result.output


@pytest.mark.parametrize(
    "callable_",
    (
        async_batch_upload,
        upload_files,
        async_ubox,
        async_download,
        get_decryptor,
        Crypt4GHDecryptor,
        get_private_key,
    ),
)
def test_nothing_takes_a_passphrase(callable_):
    """No passphrase may be passed around, so the interactive prompt stays the only
    way to provide one.
    """
    assert "passphrase" not in inspect.signature(callable_).parameters


def test_unencrypted_key_is_not_asked_about(prompts):
    """A key that is not encrypted must be read without asking the user anything"""
    private_key = get_private_key(UNENCRYPTED_KEY)

    assert not prompts
    assert private_key.get_secret_value()


def test_prompt_for_encrypted_key(prompts):
    """An encrypted key must be unlocked with an interactively entered passphrase"""
    private_key = get_private_key(ENCRYPTED_KEY)

    assert len(prompts) == 1
    expected_key = crypt4gh.keys.get_private_key(
        ENCRYPTED_KEY, callback=lambda: ENCRYPTED_KEY_PASSPHRASE
    )
    assert private_key.get_secret_value() == expected_key


def test_wrong_passphrase(monkeypatch):
    """A wrong passphrase must be reported as such instead of killing the process"""
    prompts = patch_prompt(monkeypatch, lambda: "not the passphrase")

    with pytest.raises(exceptions.InvalidPassphraseError):
        get_private_key(ENCRYPTED_KEY)

    assert len(prompts) == 1


def test_encrypted_key_without_passphrase(monkeypatch):
    """Skipping the prompt for an encrypted key must be explained, not swallowed"""
    patch_prompt(monkeypatch, lambda: "")

    with pytest.raises(exceptions.PassphraseRequiredError):
        get_private_key(ENCRYPTED_KEY)


def test_passphrase_from_environment(monkeypatch, prompts):
    """An unattended run must be able to supply the passphrase via the environment"""
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, ENCRYPTED_KEY_PASSPHRASE)

    private_key = get_private_key(ENCRYPTED_KEY)

    # the environment answers the question, so the user is not asked
    assert not prompts
    assert private_key.get_secret_value()


def test_wrong_passphrase_in_environment(monkeypatch, prompts):
    """A wrong passphrase in the environment must be reported like any other"""
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, "not the passphrase")

    with pytest.raises(exceptions.InvalidPassphraseError):
        get_private_key(ENCRYPTED_KEY)

    assert not prompts


def test_empty_passphrase_in_environment_still_prompts(monkeypatch, prompts):
    """An empty variable must not count as an answer, as it cannot unlock anything"""
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, "")

    private_key = get_private_key(ENCRYPTED_KEY)

    assert len(prompts) == 1
    assert private_key.get_secret_value()


def test_unreadable_key(prompts, tmp_path: Path):
    """A key file that cannot be parsed must be reported as such"""
    broken_key = tmp_path / "broken.sec"
    broken_key.write_text("this is not a key\n")

    with pytest.raises(exceptions.PrivateKeyFileInvalidError):
        get_private_key(broken_key)


def test_missing_key_file(prompts, tmp_path: Path):
    """A key path that does not exist must be reported before anything is asked"""
    with pytest.raises(exceptions.PrivateKeyFileDoesNotExistError):
        get_private_key(tmp_path / "nonexistent.sec")

    assert not prompts


def test_no_terminal_means_no_passphrase():
    """Without a terminal the passphrase must not be read from stdin in plain text.

    Pytest runs without a terminal on stdin, so this exercises the real prompt.
    """
    assert prompt_for_passphrase() is None


def test_unencrypted_key_works_without_terminal():
    """Scripts and CI must keep working with keys that need no passphrase"""
    private_key = get_private_key(UNENCRYPTED_KEY)

    assert private_key.get_secret_value()


def test_encrypted_key_without_terminal():
    """An encrypted key without a terminal must be explained, not exited on.

    The explanation has to name both ways out, as the user cannot be asked here.
    """
    with pytest.raises(exceptions.PassphraseRequiredError) as error:
        get_private_key(ENCRYPTED_KEY)

    assert "interactive terminal" in str(error.value)
    assert PASSPHRASE_ENV_VAR in str(error.value)


def test_encrypted_key_without_terminal_but_with_environment(monkeypatch):
    """The environment must make an encrypted key usable where nothing can be asked"""
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, ENCRYPTED_KEY_PASSPHRASE)

    private_key = get_private_key(ENCRYPTED_KEY)

    assert private_key.get_secret_value()


def test_terminal_without_input(monkeypatch):
    """A terminal that has no (more) input counts as an empty answer"""

    class TerminalWithoutInput:
        """Stand-in for a terminal the user closed the input of, e.g. with Ctrl+D"""

        def isatty(self) -> bool:
            return True

    def raise_eof(*args, **kwargs) -> str:
        raise EOFError()

    monkeypatch.setattr("sys.stdin", TerminalWithoutInput())
    monkeypatch.setattr("ghga_connector.core.utils.getpass", raise_eof)

    assert prompt_for_passphrase() is None


def test_passphrase_is_not_asked_for_in_the_clear(monkeypatch, capsys):
    """A terminal whose echo cannot be turned off must not be asked at all.

    `getpass` falls back to reading the passphrase as plain, visible text in that
    case, which would put it on screen and into any terminal log.
    """

    class TerminalWithEcho:
        """Stand-in for a terminal `getpass` cannot turn the echo off on"""

        def isatty(self) -> bool:
            return True

        def readline(self) -> str:
            raise AssertionError("the passphrase must not be read in the clear")

    monkeypatch.setattr("sys.stdin", TerminalWithEcho())
    # the real fallback: it warns, then reads from stdin in plain text
    monkeypatch.setattr("ghga_connector.core.utils.getpass", fallback_getpass)

    assert prompt_for_passphrase() is None
    assert "may be echoed" not in capsys.readouterr().err


def test_crypt4gh_noise_is_suppressed(monkeypatch, capsys):
    """crypt4gh's own error output must not compete with the connector's messages"""
    patch_prompt(monkeypatch, lambda: "not the passphrase")

    with pytest.raises(exceptions.InvalidPassphraseError):
        get_private_key(ENCRYPTED_KEY)

    assert "Invalid Key or Passphrase" not in capsys.readouterr().err


def test_decrypt_prompts_only_once(prompts, tmp_path: Path):
    """Decrypting a whole directory must only ask for the passphrase a single time"""
    contents = encrypt_files(tmp_path, count=2)
    prompts.clear()

    result = CliRunner().invoke(
        cli,
        [
            "decrypt",
            "--input-dir",
            str(tmp_path),
            "--my-private-key-path",
            str(ENCRYPTED_KEY),
        ],
    )

    assert result.exit_code == 0
    assert len(prompts) == 1
    for name, content in contents.items():
        assert (tmp_path / name).read_bytes() == content


def test_decrypt_reports_key_error_once(prompts, tmp_path: Path):
    """A broken key must be reported once, not as a failure of every single file"""
    encrypt_files(tmp_path, count=3)
    broken_key = tmp_path / "broken.sec"
    broken_key.write_text("this is not a key\n")

    result = CliRunner().invoke(
        cli,
        [
            "decrypt",
            "--input-dir",
            str(tmp_path),
            "--my-private-key-path",
            str(broken_key),
        ],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, exceptions.PrivateKeyFileInvalidError)
    # the key is read before any file is touched, so the problem is reported as one
    #  error about the key instead of one failure per file
    assert "could not be decrypted" not in result.output
    assert not prompts


def test_decrypt_fails_when_no_file_could_be_decrypted(prompts, tmp_path: Path):
    """Failing to decrypt every file must not be reported as success"""
    contents = encrypt_files(tmp_path, count=2)
    for name in contents:
        # occupy the output paths so that no file can be written
        (tmp_path / name).write_bytes(b"in the way")

    result = CliRunner().invoke(
        cli,
        [
            "decrypt",
            "--input-dir",
            str(tmp_path),
            "--my-private-key-path",
            str(ENCRYPTED_KEY),
        ],
    )

    assert result.exit_code == 1
    assert "will not overwrite" in result.output


def test_decrypt_does_not_prompt_without_files(prompts, tmp_path: Path):
    """An empty input directory must not ask for a passphrase"""
    result = CliRunner().invoke(
        cli,
        [
            "decrypt",
            "--input-dir",
            str(tmp_path),
            "--my-private-key-path",
            str(ENCRYPTED_KEY),
        ],
    )

    assert result.exit_code == 0
    assert not prompts
