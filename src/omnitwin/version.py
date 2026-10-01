"""Versienummer van D-OmniTwin.

Eén bron: het bestand `VERSION` in de root van de repository (Semantic Versioning).
Zie docs/9-beheer/releasebeleid.md.
"""
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

__version__ = VERSION_FILE.read_text(encoding="utf-8").strip()
