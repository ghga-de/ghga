# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Utilities for working with file names and formats."""

from os.path import splitext

__all__ = [
    "FILE_COMPRESSION_EXTENSIONS",
]

FILE_COMPRESSION_EXTENSIONS = {
    ".br",
    ".bz2",
    ".genozip",
    ".gz",
    ".lz",
    ".lz4",
    ".lzma",
    ".rz",
    ".sz",
    ".xz",
    ".z",
    ".zst",
}


def get_file_extension(filename: str) -> str:
    """Get file extension for the given filename.

    The extension can be composed to indicate additional compression,
    and it will always be converted to lower case.
    If the file extension indicates a (compressed) archive or package,
    then only that extension will be returned, since the actual filenames
    and their extensions are contained in the archive.
    """
    extensions = []
    while True:
        filename, ext = splitext(filename)
        if not ext or ext[1:].isdigit():
            break
        ext = ext.lower()
        extensions.append(ext)
        if ext not in FILE_COMPRESSION_EXTENSIONS:
            break
    return "".join(reversed(extensions))
