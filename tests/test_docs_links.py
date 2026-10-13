"""
Unit test: geen dode relatieve links in de Markdown-bestanden (#204).

Zie tools/check_links.py (ook los te draaien). Externe links en docs/archief/ vallen erbuiten.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

pytestmark = pytest.mark.unit


def _git_repo() -> bool:
    if not shutil.which("git"):
        return False
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True)
    return r.returncode == 0


@pytest.mark.skipif(not _git_repo(), reason="git of een git-werkmap ontbreekt (de check leest git ls-files)")
def test_geen_dode_links_in_markdown():
    import check_links

    fouten = check_links.dode_links()
    assert not fouten, "Dode links:\n" + "\n".join(fouten)
