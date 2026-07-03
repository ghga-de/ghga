"""Seed ``<PKG>_CONFIG_YAML`` from this member's ``dev_config.yaml``.

pytest roots at the member (each member has its own ``pyproject.toml``), so config seeding
must live at the member root, not the repo root. This replicates the ambient env var the
legacy per-repo CI (``gh-action-common``) and the devcontainer (docker-compose) always set,
which the module-level ``CONFIG = Config()`` in some services needs at import time.
``setdefault`` means an explicitly-exported value (CI, shell, VS Code) still wins.
"""

import os
from pathlib import Path

_here = Path(__file__).parent
_cfg = _here / "dev_config.yaml"
_src = _here / "src"
if _cfg.is_file() and _src.is_dir():
    _pkgs = [p.name for p in _src.iterdir() if (p / "__init__.py").is_file()]
    if len(_pkgs) == 1:  # config prefix == the member's single src package
        os.environ.setdefault(f"{_pkgs[0].upper()}_CONFIG_YAML", str(_cfg.resolve()))
