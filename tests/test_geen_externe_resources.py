"""
Geen externe CDN's of font-domeinen in de frontend (#117).

Bibliotheken en lettertypen worden zelf gehost onder static/vendor/. Deze test
faalt als een template of statische HTML/CSS-pagina nog naar een extern domein
verwijst dat niet expliciet is toegestaan.

Toegestaan zijn alleen data-API's (de pagina haalt er data, geen code of
opmaak, vandaan) en hyperlinks (<a href>) waar de gebruiker zelf op klikt.
"""
import re
import unittest
from pathlib import Path

try:  # CI draait `pytest -m unit`; de test zelf is gewoon unittest
    import pytest

    pytestmark = pytest.mark.unit
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent

# Domeinen die de frontend wél mag aanspreken, met reden.
TOEGESTANE_DOMEINEN = {
    "api.pdok.nl": "data-API: BRT-achtergrondkaart (stijl, tegels)",
    "service.pdok.nl": "data-API: externe kaartlagen (WMS/WMTS)",
    "www.w3.org": "XML-namespace (xmlns), wordt niet geladen",
}

# Bekende CDN- en font-domeinen: mogen buiten commentaar nergens voorkomen, ook niet in een hyperlink.
VERBODEN_DOMEINEN = (
    "unpkg.com",
    "cdn.jsdelivr.net",
    "jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
    "cdn.tailwindcss.com",
    "d3js.org",
    "code.jquery.com",
    "ajax.googleapis.com",
    "use.typekit.net",
    "use.fontawesome.com",
    "kit.fontawesome.com",
    "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",
    "cdn.skypack.dev",
    "esm.sh",
)

COMMENTAAR = re.compile(r"<!--.*?-->|/\*.*?\*/", re.S)
HYPERLINK = re.compile(r"<a\b[^>]*>", re.I | re.S)
# Absolute URL (http/https) of protocol-relatieve URL direct na een quote, = of (
PROTOCOL_RELATIEF = re.compile(r"""["'(=]\s*//([a-z0-9.-]+\.[a-z]{2,})""", re.I)
ABSOLUUT = re.compile(r"""https?://([a-z0-9.-]+\.[a-z]{2,})""", re.I)


def te_controleren_bestanden():
    bestanden = sorted((ROOT / "templates").glob("*.html"))
    static = ROOT / "static"
    for patroon in ("*.html", "*.css"):
        for pad in static.rglob(patroon):
            # Swagger UI is een gebundelde, lokale build zonder externe resources;
            # vendor-bestanden zijn byte-gelijke kopieën van npm-pakketten.
            if "swagger-ui" in pad.parts or "vendor" in pad.parts:
                continue
            bestanden.append(pad)
    return bestanden


def domeinen_in(tekst):
    """Externe domeinen in resource-verwijzingen, zonder commentaar en hyperlinks."""
    tekst = COMMENTAAR.sub(" ", tekst)
    tekst = HYPERLINK.sub(" ", tekst)
    gevonden = set(m.group(1).lower() for m in ABSOLUUT.finditer(tekst))
    gevonden |= set(m.group(1).lower() for m in PROTOCOL_RELATIEF.finditer(tekst))
    return gevonden


class TestGeenExterneResources(unittest.TestCase):
    def test_er_zijn_bestanden_om_te_controleren(self):
        namen = [p.name for p in te_controleren_bestanden()]
        self.assertIn("index.html", namen)
        self.assertIn("help.html", namen)

    def test_geen_cdn_of_font_domein(self):
        fouten = []
        for pad in te_controleren_bestanden():
            tekst = COMMENTAAR.sub(" ", pad.read_text(encoding="utf-8", errors="replace")).lower()
            for domein in VERBODEN_DOMEINEN:
                if re.search(r"(?<![a-z0-9.-])" + re.escape(domein), tekst):
                    fouten.append(f"{pad.relative_to(ROOT)}: {domein}")
        self.assertEqual(fouten, [], "Externe CDN/font-verwijzing gevonden; host zelf onder static/vendor/")

    def test_alleen_toegestane_externe_domeinen(self):
        fouten = []
        for pad in te_controleren_bestanden():
            tekst = pad.read_text(encoding="utf-8", errors="replace")
            for domein in sorted(domeinen_in(tekst)):
                if domein not in TOEGESTANE_DOMEINEN:
                    fouten.append(f"{pad.relative_to(ROOT)}: {domein}")
        self.assertEqual(
            fouten, [],
            "Onbekend extern domein. Host de resource zelf, of voeg een data-API "
            "met reden toe aan TOEGESTANE_DOMEINEN.",
        )

    def test_vendor_bestanden_bestaan(self):
        """Elke /static/vendor/-verwijzing in de templates wijst naar een bestaand bestand."""
        verwijzingen = set()
        for pad in te_controleren_bestanden():
            tekst = pad.read_text(encoding="utf-8", errors="replace")
            verwijzingen |= set(re.findall(r"/static/vendor/[^\"')\s>]+", tekst))
        self.assertTrue(verwijzingen, "geen vendor-verwijzingen gevonden")
        ontbrekend = [v for v in sorted(verwijzingen) if not (ROOT / v.lstrip("/")).is_file()]
        self.assertEqual(ontbrekend, [])

    def test_detectie_werkt(self):
        """Zelftest: de regexen vangen de vormen die we willen blokkeren."""
        self.assertEqual(domeinen_in('<script src="https://unpkg.com/x.js"></script>'), {"unpkg.com"})
        self.assertEqual(domeinen_in("@import url('//fonts.googleapis.com/css')"), {"fonts.googleapis.com"})
        self.assertEqual(domeinen_in('<a href="https://example.org/">link</a>'), set())
        self.assertEqual(domeinen_in("<!-- https://unpkg.com -->"), set())


if __name__ == "__main__":
    unittest.main()
