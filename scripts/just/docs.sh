#!/usr/bin/env bash
# `just docs [member]`: build the documentation site(s) into <member>/great-docs/_site.
#
# A member is documented iff it carries a `great-docs.yml`; scripts/docs_members.py is the
# same discovery docs-publish.yaml reads, so a local build cannot drift from the deployed one.
set -euo pipefail

root=$(git rev-parse --show-toplevel)
[ -x "$root/.venv-docs/bin/great-docs" ] || {
    echo "error: the docs toolchain is not installed. Run: just docs-install" >&2
    exit 1
}
# great-docs renders through Quarto, which is a separate binary rather than a Python
# dependency, so the docs venv being present is not enough on its own.
command -v quarto > /dev/null || {
    echo "error: the Quarto CLI is not on PATH, and great-docs renders with it." >&2
    echo "The devcontainer provisions it; rebuild the container, or install it from" >&2
    echo "https://quarto.org/docs/get-started/ to build the docs on a bare host." >&2
    exit 1
}
# A declared URL that disagrees with the deploy subpath breaks canonical links, the
# sitemap and asset resolution silently, so it is checked before anything is rendered.
uv run --script "$root/scripts/docs_members.py" --check
members="${1:-}"
[ -n "$members" ] || members=$(uv run --script "$root/scripts/docs_members.py")
for member in $members; do
    [ -f "$root/$member/great-docs.yml" ] || {
        echo "error: $member carries no great-docs.yml, so it is not documented." >&2
        exit 1
    }
    echo "== great-docs build $member =="
    # cwd = the member directory: great-docs resolves great-docs.yml, the pre_render
    # hooks and its build output relative to it.
    (cd "$root/$member" && "$root/.venv-docs/bin/great-docs" build)
done
