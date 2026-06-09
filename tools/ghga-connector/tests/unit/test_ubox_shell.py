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

"""Unit tests for the interactive upload box shell."""

from pathlib import Path
from uuid import uuid4

import pytest
from prompt_toolkit.document import Document
from pydantic import SecretBytes

from ghga_connector.core.uploading import ubox_shell
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.structs import UploadedFileInfo
from ghga_connector.core.uploading.ubox_shell import (
    UboxCompleter,
    UboxShell,
    _expand_globs,
    _extract_alias,
    _format_listing,
    _human_readable_size,
)


class FakeUploadClient(UploadClient):
    """A stand-in for UploadClient that records interactions.

    Only the methods exercised by the ``ls`` and ``rm`` commands are
    implemented; the upload path is patched out in the tests that need it.
    """

    def __init__(self, uploads: list[UploadedFileInfo] | None = None):
        self.uploads = uploads if uploads is not None else []
        self.deleted: list[tuple] = []

    async def get_box_uploads(self) -> list[UploadedFileInfo]:
        """Return the current box contents."""
        return list(self.uploads)

    async def delete_file(self, *, file_id, file_alias) -> None:
        """Record the deletion and drop the file from the box."""
        self.deleted.append((file_id, file_alias))
        self.uploads = [u for u in self.uploads if u.file_id != file_id]


def _make_info(alias: str, **kwargs) -> UploadedFileInfo:
    return UploadedFileInfo.model_validate(
        {"id": str(uuid4()), "alias": alias, **kwargs}
    )


def test_extract_alias_variants():
    """The --alias option is parsed in both space and equals forms."""
    assert _extract_alias(["--alias", "foo", "a.bam"]) == ("foo", ["a.bam"])
    assert _extract_alias(["--alias=bar", "a.bam"]) == ("bar", ["a.bam"])
    assert _extract_alias(["a.bam", "b.bam"]) == (None, ["a.bam", "b.bam"])


@pytest.mark.parametrize(
    "args",
    [
        ["--alias"],
        ["--alias="],
        ["--alias", "x", "--alias", "y", "path"],
    ],
)
def test_extract_alias_errors(args):
    """Invalid --alias usage raises a ValueError."""
    with pytest.raises(ValueError):
        _extract_alias(args)


def test_expand_globs(tmp_path: Path):
    """Globs are expanded; non-matching tokens pass through unchanged."""
    (tmp_path / "one.bam").write_text("data")
    (tmp_path / "two.bam").write_text("data")

    expanded = _expand_globs([str(tmp_path / "*.bam")])
    assert sorted(Path(p).name for p in expanded) == ["one.bam", "two.bam"]

    # Non-matching token is preserved verbatim for downstream validation
    missing = str(tmp_path / "missing_*.xyz")
    assert _expand_globs([missing]) == [missing]


def test_human_readable_size():
    """Byte counts are rendered compactly."""
    assert _human_readable_size(None) == "-"
    assert _human_readable_size(512) == "512 B"
    assert _human_readable_size(1024) == "1.0 KiB"
    assert _human_readable_size(1024**2) == "1.0 MiB"


def test_format_listing_contains_fields():
    """The listing table contains the header and per-file values."""
    info = _make_info("a.bam", decrypted_size=2048, state="inbox")
    rendered = _format_listing([info])
    assert "ALIAS" in rendered
    assert "a.bam" in rendered
    # The raw "inbox" state is shown under its user-facing label.
    assert "re-encrypting..." in rendered
    assert "inbox" not in rendered
    assert str(info.file_id) in rendered


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("inbox", "re-encrypting..."),
        ("interrogated", "re-encrypted"),
        ("cancelled", "deleted"),
        ("Cancelled", "deleted"),  # case-insensitive
        ("populated", "populated"),  # unmapped states pass through
        (None, "-"),
    ],
)
def test_display_state(state, expected):
    """Raw API states are mapped to user-facing labels."""
    assert ubox_shell._display_state(state) == expected


@pytest.mark.asyncio
async def test_do_ls_empty(capsys):
    """The ls command on an empty box reports that it is empty."""
    shell = UboxShell(upload_client=FakeUploadClient(), my_private_key=SecretBytes(b""))
    await shell._do_ls([])
    assert "empty" in capsys.readouterr().out.lower()


@pytest.mark.asyncio
async def test_do_ls_hides_cancelled_by_default(capsys):
    """Cancelled files are omitted from the listing unless requested."""
    client = FakeUploadClient(
        [
            _make_info("active.bam", state="inbox"),
            _make_info("gone.bam", state="cancelled"),
        ]
    )
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_ls([])

    out = capsys.readouterr().out
    assert "active.bam" in out
    assert "gone.bam" not in out


@pytest.mark.asyncio
async def test_do_ls_show_deleted(capsys):
    """The --show-deleted flag includes cancelled files, shown as 'deleted'."""
    client = FakeUploadClient(
        [
            _make_info("active.bam", state="inbox"),
            _make_info("gone.bam", state="cancelled"),
        ]
    )
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_ls(["--show-deleted"])

    out = capsys.readouterr().out
    assert "active.bam" in out
    assert "gone.bam" in out
    assert "deleted" in out


@pytest.mark.asyncio
async def test_do_ls_all_deleted_message(capsys):
    """A box holding only cancelled files reports that, not 'empty'."""
    client = FakeUploadClient([_make_info("gone.bam", state="Cancelled")])
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_ls([])

    out = capsys.readouterr().out.lower()
    assert "deleted" in out
    assert "--show-deleted" in out


@pytest.mark.asyncio
async def test_do_ls_rejects_unknown_flag(capsys):
    """An unrecognised ls argument is rejected with a usage message."""
    client = FakeUploadClient([_make_info("active.bam", state="inbox")])
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_ls(["--nope"])

    assert "usage" in capsys.readouterr().err.lower()


@pytest.mark.asyncio
async def test_do_rm_success():
    """The rm command resolves an alias to its file ID and deletes it."""
    info = _make_info("a.bam", decrypted_size=2048)
    client = FakeUploadClient([info])
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_rm(["a.bam"])

    assert client.deleted == [(info.file_id, "a.bam")]
    assert client.uploads == []


@pytest.mark.asyncio
async def test_do_rm_unknown_alias(capsys):
    """The rm command on a missing alias reports an error and deletes nothing."""
    client = FakeUploadClient([_make_info("a.bam")])
    shell = UboxShell(upload_client=client, my_private_key=SecretBytes(b""))

    await shell._do_rm(["does-not-exist"])

    assert client.deleted == []
    assert "does-not-exist" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_do_upload_glob(monkeypatch, tmp_path: Path):
    """The upload command with a glob uploads each match using its file name."""
    for name in ("one.bam", "two.bam"):
        (tmp_path / name).write_text("plaintext content")

    captured: list[list[tuple[str, str]]] = []

    async def fake_upload_files_from_list(
        *, upload_client, file_info_list, my_private_key, max_concurrent_uploads
    ):
        captured.append([(fi.alias, Path(fi.path).name) for fi in file_info_list])

    monkeypatch.setattr(
        ubox_shell, "upload_files_from_list", fake_upload_files_from_list
    )

    shell = UboxShell(
        upload_client=FakeUploadClient(), my_private_key=SecretBytes(b"key")
    )
    await shell._do_upload([str(tmp_path / "*.bam")])

    assert len(captured) == 1
    assert sorted(captured[0]) == [("one.bam", "one.bam"), ("two.bam", "two.bam")]


@pytest.mark.asyncio
async def test_do_upload_with_alias(monkeypatch, tmp_path: Path):
    """The upload command with --alias uploads a single file under that alias."""
    target = tmp_path / "data.bam"
    target.write_text("plaintext content")

    captured: list[list[tuple[str, str]]] = []

    async def fake_upload_files_from_list(
        *, upload_client, file_info_list, my_private_key, max_concurrent_uploads
    ):
        captured.append([(fi.alias, Path(fi.path).name) for fi in file_info_list])

    monkeypatch.setattr(
        ubox_shell, "upload_files_from_list", fake_upload_files_from_list
    )

    shell = UboxShell(
        upload_client=FakeUploadClient(), my_private_key=SecretBytes(b"key")
    )
    await shell._do_upload(["--alias", "custom", str(target)])

    assert captured == [[("custom", "data.bam")]]


@pytest.mark.asyncio
async def test_do_upload_alias_rejects_multiple(monkeypatch, tmp_path: Path, capsys):
    """The upload command with --alias and multiple matched files is rejected."""
    for name in ("one.bam", "two.bam"):
        (tmp_path / name).write_text("plaintext content")

    async def fail_if_called(**kwargs):  # pragma: no cover - must not run
        raise AssertionError("upload should not be attempted")

    monkeypatch.setattr(ubox_shell, "upload_files_from_list", fail_if_called)

    shell = UboxShell(
        upload_client=FakeUploadClient(), my_private_key=SecretBytes(b"key")
    )
    await shell._do_upload(["--alias", "custom", str(tmp_path / "*.bam")])

    assert "exactly one" in capsys.readouterr().err


async def _complete(completer: UboxCompleter, text: str) -> list[str]:
    """Collect the completion texts the completer yields for the given input."""
    document = Document(text, cursor_position=len(text))
    return [
        completion.text
        async for completion in completer.get_completions_async(document, None)
    ]


@pytest.mark.asyncio
async def test_complete_command_names():
    """The first word completes against the known command names."""
    completer = UboxCompleter(upload_client=FakeUploadClient())

    assert set(await _complete(completer, "")) == {
        "upload",
        "ls",
        "rm",
        "help",
        "exit",
        "quit",
    }
    assert await _complete(completer, "r") == ["rm"]
    assert sorted(await _complete(completer, "e")) == ["exit"]


@pytest.mark.asyncio
async def test_complete_ls_flag():
    """The ls command completes --show-deleted, but only once."""
    completer = UboxCompleter(upload_client=FakeUploadClient())

    assert await _complete(completer, "ls ") == ["--show-deleted"]
    assert await _complete(completer, "ls --s") == ["--show-deleted"]
    # Already present, so it is not offered again.
    assert await _complete(completer, "ls --show-deleted ") == []


@pytest.mark.asyncio
async def test_complete_rm_remote_aliases():
    """The rm command completes against box aliases, prefix-filtered."""
    client = FakeUploadClient([_make_info("alpha.vcf"), _make_info("beta.bam")])
    completer = UboxCompleter(upload_client=client)

    assert sorted(await _complete(completer, "rm ")) == ["alpha.vcf", "beta.bam"]
    assert await _complete(completer, "rm al") == ["alpha.vcf"]
    # rm takes a single alias, so a second argument is not completed.
    assert await _complete(completer, "rm alpha.vcf ") == []


@pytest.mark.asyncio
async def test_complete_upload_local_paths(tmp_path: Path):
    """The upload command completes against local filesystem paths."""
    (tmp_path / "sample1.txt").write_text("data")
    (tmp_path / "sample2.txt").write_text("data")
    completer = UboxCompleter(upload_client=FakeUploadClient())

    completions = await _complete(completer, f"upload {tmp_path}/sam")
    # PathCompleter completes the remainder after the typed prefix.
    assert sorted(completions) == ["ple1.txt", "ple2.txt"]


@pytest.mark.asyncio
async def test_complete_upload_alias_flag():
    """A leading dash on an upload argument completes the --alias flag."""
    completer = UboxCompleter(upload_client=FakeUploadClient())
    assert await _complete(completer, "upload -") == ["--alias"]


@pytest.mark.asyncio
async def test_complete_upload_suppresses_alias_value(tmp_path: Path):
    """No completion is offered for the user-chosen value right after --alias."""
    (tmp_path / "sample.txt").write_text("data")
    completer = UboxCompleter(upload_client=FakeUploadClient())

    # Typing the alias value itself yields nothing...
    assert await _complete(completer, "upload --alias my") == []
    # ...but the following positional argument resumes path completion.
    assert await _complete(completer, f"upload --alias myname {tmp_path}/sam") == [
        "ple.txt"
    ]


@pytest.mark.asyncio
async def test_complete_rm_alias_cache(monkeypatch):
    """Remote aliases are cached within the TTL and refetched once it elapses."""
    calls = 0

    class CountingClient(FakeUploadClient):
        async def get_box_uploads(self):
            nonlocal calls
            calls += 1
            return list(self.uploads)

    client = CountingClient([_make_info("alpha.vcf")])
    completer = UboxCompleter(upload_client=client)

    clock = {"now": 1000.0}
    monkeypatch.setattr(ubox_shell.time, "monotonic", lambda: clock["now"])

    await _complete(completer, "rm ")
    await _complete(completer, "rm a")
    assert calls == 1  # second lookup served from cache

    clock["now"] += ubox_shell._ALIAS_CACHE_TTL + 1
    await _complete(completer, "rm ")
    assert calls == 2  # cache expired, refetched
