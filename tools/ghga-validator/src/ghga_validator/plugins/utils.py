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

"""Utils for plugins"""

import importlib
import pkgutil

import ghga_validator.plugins as plugin_package


def discover_plugins(plugin_type) -> dict:
    """Discover all plugins of a type"""
    discovered_plugins = {}
    for _, module_name, _ in pkgutil.iter_modules(plugin_package.__path__):
        try:
            module = importlib.import_module(f"{plugin_package.__name__}.{module_name}")
            for name, cls in module.__dict__.items():
                if isinstance(cls, type) and issubclass(cls, plugin_type):
                    discovered_plugins[name] = cls
        except ImportError as err:
            print(f"Error loading module '{module_name}': {err}")
    return discovered_plugins
