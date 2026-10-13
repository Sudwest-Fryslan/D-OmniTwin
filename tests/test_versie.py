"""
Unit test: één versienummer (#27).

`VERSION` is de bron. `publiccode.yml`, `admin-panel/package.json` en de app
(`src/omnitwin/version.py`, gebruikt door `src/omnitwin/main.py`) moeten hetzelfde nummer hebben, en het
moet geldige Semantic Versioning zijn. Zie docs/9-beheer/releasebeleid.md.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.unit

# Officiële regex van semver.org
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _bron() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_version_is_semver():
    assert SEMVER.match(_bron()), f"VERSION is geen geldige semver: {_bron()!r}"


def test_app_leest_version():
    from omnitwin.version import __version__

    assert __version__ == _bron()


def test_main_gebruikt_version():
    main = (ROOT / "src" / "omnitwin" / "main.py").read_text(encoding="utf-8")
    assert "from omnitwin.version import __version__" in main
    assert "version=__version__" in main
    # Geen losse, hardgecodeerde versienummers meer in main.py
    assert not re.search(r"""["']version["']\s*:\s*["']\d""", main)
    assert not re.search(r"""version\s*=\s*["']\d""", main)


def test_publiccode_softwareversion():
    tekst = (ROOT / "publiccode.yml").read_text(encoding="utf-8")
    m = re.search(r"""^softwareVersion:\s*["']?([^"'\s#]+)""", tekst, re.MULTILINE)
    assert m, "softwareVersion ontbreekt in publiccode.yml"
    assert m.group(1) == _bron()


def test_admin_package_json():
    pkg = json.loads((ROOT / "admin-panel" / "package.json").read_text(encoding="utf-8"))
    assert pkg["version"] == _bron()


def test_footer_toont_app_version():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "{{ app_version }}" in html
