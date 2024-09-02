# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Fixture for testing code that uses the FileObject provider."""

import csv
import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

from hexkit.providers.s3.testutils import FileObject
from pydantic import BaseModel
from pytest import fixture

from fixtures.config import Config
from fixtures.dsk import DskFixture
from fixtures.utils import calculate_checksum

__all__ = ["FileBatch", "FileObject", "file_fixture"]


class FileBatch(BaseModel):
    """File batch model"""

    file_objects: list[FileObject]
    tsv_file: Path


def subset_file_batch_by_scope(file_batch: FileBatch, file_scope: str) -> FileBatch:
    """Return subset of files in a FileBatch based on the file extension"""
    if file_scope in {"vcf", "fastq"}:
        extension = f".{file_scope}.gz"
    elif file_scope in {"txt", "json"}:
        extension = f".{file_scope}"
    else:
        raise ValueError(f"Unknown file scope: {file_scope}")

    subset_file_objects = []
    scoped_tsv_file = file_batch.tsv_file.parent / f"filtered_{file_scope}.tsv"
    with open(file_batch.tsv_file) as infile, open(scoped_tsv_file, "w") as outfile:
        reader = csv.reader(infile, delimiter="\t")
        writer = csv.writer(outfile, delimiter="\t")

        for row in reader:
            file_path = row[0]
            if file_path.endswith(extension):
                writer.writerow(row)
                file_object = next(
                    (
                        file_obj
                        for file_obj in file_batch.file_objects
                        if file_obj.file_path == Path(file_path)
                    ),
                    None,
                )
                if file_object:
                    subset_file_objects.append(file_object)

    return FileBatch(file_objects=subset_file_objects, tsv_file=Path(scoped_tsv_file))


def create_named_file(
    target_dir: Path,
    config: Config,
    name: str,
    alias: str | None = None,
    file_size: int | None = None,
) -> FileObject:
    """Create a file with given parameters"""
    file_path = target_dir / name

    if not alias:
        alias = os.path.splitext(name)[0]

    file_size = config.default_file_size if file_size is None else file_size

    with open(file_path, "wb") as file:
        first_line = f"{alias}\n".encode()
        if file_size <= len(first_line):
            first_line = first_line[:file_size]
            file.write(first_line)
        else:
            remaining_bytes = file_size - len(first_line)
            content = first_line + b"\0" * remaining_bytes
            file.write(content)

    file_object = FileObject(
        file_path=Path(file_path),
        bucket_id=config.staging_bucket,
        object_id=alias,
    )
    return file_object


@fixture(name="file_fixture")
def file_fixture(
    config: Config, dsk: DskFixture
) -> Generator[dict[str, FileBatch], None, None]:
    """Batch file fixture that provides temporary files for the metadata.

    File sizes are distributed according to the number of files in the metadata.
    """
    temp_dir = Path(tempfile.gettempdir())
    metadata = json.loads(dsk.config.complete_metadata_path.read_text())
    datasets: dict[str, list[dict]] = {
        dataset["alias"]: [] for dataset in metadata["datasets"]
    }
    assert set(datasets) == {"DS_A", "DS_B"}
    for file_field in dsk.config.metadata_file_fields:
        for file in metadata[file_field]:
            datasets[file["dataset"]].append(file)

    file_batches: dict[str, FileBatch] = {}
    for dataset, files in datasets.items():
        files_to_upload_tsv = dsk.config.submission_registry / f"{dataset}_files.tsv"
        created_files = []
        with open(files_to_upload_tsv, "w", encoding="utf-8") as tsv_file:
            file_sizes = (
                [3]  # See create_named_file(), for file content/alias truncation.
                + [
                    round(config.default_file_size / (len(files) - 1)) * i
                    for i in range(1, len(files) - 1)
                ]
                + [config.default_file_size]
            )  # Distribution of file sizes to the file count
            for i, file_ in enumerate(files):
                file_object = create_named_file(
                    target_dir=temp_dir,
                    config=config,
                    name=file_["name"],
                    alias=file_["alias"],
                    file_size=file_sizes[i],
                )

                created_files.append(file_object)
                tsv_file.write(f"{file_object.file_path}\t{file_object.object_id}\n")

        file_batches.update(
            {
                dataset: FileBatch(
                    file_objects=created_files, tsv_file=files_to_upload_tsv
                )
            }
        )

    yield file_batches

    for file_batch in file_batches.values():
        for file_object in file_batch.file_objects:
            os.remove(file_object.file_path)
