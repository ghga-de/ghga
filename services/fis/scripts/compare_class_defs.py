#!/usr/bin/env python3

# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Script to keep ABC classes and their implementations in sync"""

import inspect

from fis.core.interrogation import InterrogationHandler  # noqa: F401

# Import the abstract base classes and their implementations
from fis.ports.inbound.interrogation import InterrogationHandlerPort

PORTS = [InterrogationHandlerPort]


def print_links(abc_method: type, imp_method: type):
    """Print file path and line number of the method"""
    abc_file = inspect.getfile(abc_method)
    imp_file = inspect.getfile(imp_method)
    abc_line = inspect.getsourcelines(abc_method)[1]
    imp_line = inspect.getsourcelines(imp_method)[1]
    print(f'  ABC: "{abc_file}", line {abc_line}')
    print(f'  Imp: "{imp_file}", line {imp_line}')


def check_implementation(abc_class: type):
    """Check that the implementation class matches the abstract base class"""
    # infer the implementation class from the abstract base class
    imp_class = abc_class.__subclasses__()[0]

    # Get public methods (as a general rule, don't check private methods)
    methods = [m for m in abc_class.__abstractmethods__ if not m.startswith("_")]  # type: ignore
    found_issues = False
    for method in methods:
        abc_method = getattr(abc_class, method)
        imp_method = getattr(imp_class, method)

        # Check method doc string
        if imp_method.__doc__ != abc_method.__doc__:
            print(
                f"`{method}` doc string mismatch between {abc_class.__name__} and {imp_class.__name__}"
            )
            print_links(abc_method, imp_method)
            found_issues = True

        # Check method signature
        if inspect.signature(imp_method) != inspect.signature(abc_method):
            print(
                f"`{method}` function signature mismatch between {abc_class.__name__} and {imp_class.__name__}"
            )
            print_links(abc_method, imp_method)
            found_issues = True
    if not found_issues:
        print(f"✓  {imp_class.__name__} <---> {abc_class.__name__}")


def main():
    """Test me"""
    for port in PORTS:
        check_implementation(port)


if __name__ == "__main__":
    main()
