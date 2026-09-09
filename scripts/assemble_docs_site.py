#!/usr/bin/env python3
# Imports docs_members for SITE_URL, the one definition of where the site is served from,
# so the generated links cannot disagree with the members' own `site_url`. That module
# reads YAML, hence the same PEP 723 dependency and the same `uv run --script` invocation.
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Assemble the per-member documentation builds into the single Pages site (ADR-0021).

Each member's built `_site` becomes `<package>/` in the site root. The root itself gets
an index listing them, and a 404 page.

The 404 page matters more than it looks. Every retired per-package docs site redirects
here by path, and those redirects live on archived repositories that can no longer run
Actions — so if a page is renamed or removed on this side, the old link forwards to a URL
that no longer exists and the redirecting side cannot be fixed. This page is the only
remaining place to catch that, so it names the path that was requested and points at the
package it belongs to rather than dead-ending.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    uv run --script scripts/docs_members.py --json \\
      | uv run --script scripts/assemble_docs_site.py --artifacts artifacts --out site
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import shutil
import sys
from urllib.parse import urlsplit

from docs_members import SITE_URL

# Served for arbitrary paths, so every link on these pages is absolute from the site root:
# a relative href on /ghga/hexkit/gone/deep.html would resolve against the missing page.
SITE_PATH = urlsplit(SITE_URL).path.rstrip("/") + "/"

STYLE = """\
  :root { color-scheme: light dark }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.5;
         max-width: 40rem; margin: 0 auto; padding: 2rem 1.25rem }
  h1 { font-size: 1.5rem; margin-bottom: .25rem }
  code { overflow-wrap: anywhere }
  ul { padding-left: 1.25rem }
  .muted { opacity: .75; font-size: .9375rem }
"""


def _page(title: str, body: str, script: str = "") -> str:
    """Wraps a page body in the shared shell."""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>\n{STYLE}</style>\n</head>\n<body>\n{body}\n{script}</body>\n</html>\n"
    )


def _member_list(members: list[dict]) -> str:
    """The documented packages, as links from the site root."""
    items = "\n".join(
        f'    <li><a href="{SITE_PATH}{html.escape(m["package"])}/">'
        f"{html.escape(m['package'])}</a></li>"
        for m in members
    )
    return f"  <ul>\n{items}\n  </ul>"


def index_page(members: list[dict]) -> str:
    """The site root: what is documented here."""
    return _page(
        "GHGA documentation",
        "  <h1>GHGA documentation</h1>\n"
        "  <p>Documentation for the packages published from the "
        '<a href="https://github.com/ghga-de/ghga">GHGA monorepo</a>:</p>\n'
        + _member_list(members),
    )


def not_found_page(members: list[dict]) -> str:
    """The 404 page, which resolves what it can about the path that was requested."""
    packages = json.dumps([m["package"] for m in members])
    body = (
        "  <h1>Page not found</h1>\n"
        '  <p id="what">There is no page at this address.</p>\n'
        '  <p id="hint" class="muted" hidden></p>\n'
        "  <p>Documented packages:</p>\n"
        + _member_list(members)
        + '\n  <p class="muted">Links from the retired per-package documentation sites '
        "redirect here by path. If a page was renamed or removed after the move, this is "
        "where the old link lands — the package's own documentation above is the place to "
        "look for it.</p>"
    )
    # Progressive enhancement: the page is already useful without this, and only ever
    # gains a sentence — it never redirects on its own. A missing page is worth showing
    # rather than papering over, and guessing a destination would hide a broken link from
    # the person best placed to report it.
    script = f"""<script>
  (function () {{
    var packages = {packages};
    var root = {json.dumps(SITE_PATH)};
    var path = location.pathname;
    document.getElementById("what").innerHTML =
      "There is no page at <code>" +
      path.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</code> on this site.";
    var rest = path.indexOf(root) === 0 ? path.slice(root.length) : "";
    var pkg = rest.split("/")[0];
    if (packages.indexOf(pkg) !== -1) {{
      var hint = document.getElementById("hint");
      hint.innerHTML =
        'That looks like a <strong>' + pkg + '</strong> page that has been renamed or ' +
        'removed. Start from <a href="' + root + pkg + '/">' + pkg +
        "'s documentation</a> and search there.";
      hint.hidden = false;
    }}
  }})();
</script>
"""
    return _page("Page not found", body, script)


def assemble(members: list[dict], artifacts: pathlib.Path, out: pathlib.Path) -> None:
    """Copies each member's built site into `out`, then writes the root pages.

    Raises:
        SystemExit: if a member has no built site, since publishing a partial site would
            silently 404 every page of whichever member failed to build.
    """
    out.mkdir(parents=True, exist_ok=True)
    for member in members:
        package = member["package"]
        built = artifacts / f"docs-{package}"
        if not built.is_dir():
            sys.exit(f"error: no built site for {package} at {built}")
        shutil.copytree(built, out / package, dirs_exist_ok=True)

    (out / "index.html").write_text(index_page(members), encoding="utf-8")
    (out / "404.html").write_text(not_found_page(members), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    members = json.loads(sys.stdin.read())
    assemble(members, args.artifacts, args.out)
    print(f"assembled {len(members)} member site(s) into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
