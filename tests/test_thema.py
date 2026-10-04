"""
Thema's (NL Design System-tokens) per organisatie (#89).

Controleert de themabestanden in static/css/themes/:
- opbouw: licht, donker en donker-via-systeeminstelling, alleen --basis-* en --d-omnitwin-* tokens
  (datakleuren horen niet in een thema);
- het standaardthema d-omnitwin is gelijk aan de fallbacks in styles.css (geen visuele regressie);
- contrast volgens WCAG 2.1 AA: 4,5:1 voor tekst (1.4.3), 3:1 voor UI-onderdelen en focus (1.4.11);
- de themanaam: alleen [a-z0-9-], anders het standaardthema;
- de regel "@wcag-aa: ja|nee" in de kop van elk thema klopt met de contrasten; een thema met "nee"
  (d-omnitwin, legacy) is nooit de standaard voor een organisatie; swf haalt voor tekst AAA (7:1) (#284).

Los draaien met een overzicht van alle contrasten: python tests/test_thema.py --rapport
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

try:  # CI draait `pytest -m unit`; de test zelf is gewoon unittest
    import pytest

    pytestmark = pytest.mark.unit
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
THEMA_MAP = ROOT / "static" / "css" / "themes"
STYLES = ROOT / "static" / "css" / "styles.css"
# Alles van de viewer en het beheerscherm (bron, geen build) dat thema-tokens kan lezen
VIEWER_BESTANDEN = [
    *sorted((ROOT / "static" / "css").glob("*.css")),
    *sorted((ROOT / "static" / "js").rglob("*.js")),
    *sorted((ROOT / "templates").glob("*.html")),
    *sorted((ROOT / "static" / "images").glob("*.svg")),
    *sorted(p for p in (ROOT / "admin-panel" / "src").rglob("*.*")
            if p.suffix in (".css", ".ts", ".tsx") and ".test." not in p.name),
]
ADMIN_CSS = ROOT / "admin-panel" / "src" / "styles" / "admin.css"

sys.path.insert(0, str(ROOT / "src"))
from omnitwin.thema import (  # noqa: E402
    STANDAARD_THEMA,
    beschikbare_themas,
    is_geldige_themanaam,
    kies_thema,
)

TEKST, UI = 4.5, 3.0
AAA = 7.0

# (voorgrond, achtergrond, minimum, omschrijving). Tokens zonder --basis-/--d-omnitwin- voorvoegsel.
PAREN = [
    ("basis-color-default-color-document", "basis-color-default-bg-document", TEKST, "tekst op pagina"),
    ("basis-color-default-color-document", "basis-color-default-bg-default", TEKST, "tekst op paneel"),
    ("basis-color-default-color-subtle", "basis-color-default-bg-document", TEKST, "secundaire tekst op pagina"),
    ("basis-color-default-color-subtle", "basis-color-default-bg-default", TEKST, "secundaire tekst op paneel"),
    ("basis-color-accent-1-color-default", "basis-color-default-bg-document", TEKST, "accenttekst/link op pagina"),
    ("basis-color-accent-1-color-default", "basis-color-default-bg-default", TEKST, "accenttekst/link op paneel"),
    ("basis-color-accent-1-color-hover", "basis-color-default-bg-default", TEKST, "link hover op paneel"),
    ("basis-color-accent-1-inverse-color-default", "basis-color-accent-1-bg-default", TEKST, "tekst op accentvlak"),
    ("basis-color-accent-1-inverse-color-default", "basis-color-accent-1-bg-hover", TEKST, "tekst op accentvlak hover"),
    ("basis-color-action-1-color-default", "basis-color-default-bg-default", TEKST, "actietekst op paneel"),
    ("basis-color-action-1-inverse-color-default", "basis-color-action-1-bg-default", TEKST, "tekst op knop"),
    ("basis-color-action-1-inverse-color-default", "basis-color-action-1-bg-hover", TEKST, "tekst op knop hover"),
    ("basis-color-accent-2-color-default", "basis-color-default-bg-document", TEKST, "accent-2-tekst op pagina"),
    ("basis-color-accent-2-color-default", "basis-color-default-bg-default", TEKST, "accent-2-tekst op paneel"),
    ("basis-color-accent-3-color-default", "basis-color-default-bg-default", TEKST, "accent-3-tekst op paneel"),
    ("basis-color-negative-color-default", "basis-color-default-bg-default", TEKST, "fouttekst op paneel"),
    ("basis-color-positive-color-default", "basis-color-default-bg-default", TEKST, "succestekst op paneel"),
    ("basis-color-warning-color-default", "basis-color-default-bg-default", TEKST, "waarschuwing op paneel"),
    ("d-omnitwin-header-color", "d-omnitwin-header-background-color-start", TEKST, "kopbalktekst (begin verloop)"),
    ("d-omnitwin-header-color", "d-omnitwin-header-background-color-end", TEKST, "kopbalktekst (eind verloop)"),
    ("basis-color-accent-2-bg-default", "basis-color-default-bg-default", UI, "accentvlak/selectie op paneel"),
    # Componenttokens (#89)
    ("d-omnitwin-tab-active-color", "d-omnitwin-tab-active-background-color", UI, "icoon op actieve tab"),
    ("d-omnitwin-welcome-button-color", "d-omnitwin-welcome-button-background-color", TEKST, "tekst op welkomstknop"),
    ("d-omnitwin-welcome-accent-color", "basis-color-default-bg-default", TEKST, "welkomstaccent op paneel"),
    ("d-omnitwin-tooltip-color", "d-omnitwin-tooltip-background-color", TEKST, "tooltiptekst"),
    ("d-omnitwin-selection-badge-color", "d-omnitwin-selection-badge-background-color", TEKST, "tekst op selectiebadge"),
    ("d-omnitwin-tab-active-border-color", "basis-color-default-bg-default", UI, "rand actieve tab op paneel"),
    ("d-omnitwin-beheer-kop-color", "d-omnitwin-beheer-kop-background-color-start", TEKST, "beheerscherm: koptekst (begin)"),
    ("d-omnitwin-beheer-kop-color", "d-omnitwin-beheer-kop-background-color-end", TEKST, "beheerscherm: koptekst (eind)"),
    ("d-omnitwin-beheer-nav-active-color", "d-omnitwin-beheer-nav-active-background-color", TEKST, "beheerscherm: actief menu-item"),
    ("basis-focus-outline-color", "basis-color-default-bg-document", UI, "focusrand op pagina"),
    ("basis-focus-outline-color", "basis-color-default-bg-default", UI, "focusrand op paneel"),
    # Alleen als het thema ze definieert:
    ("basis-color-accent-3-inverse-color-default", "basis-color-accent-3-bg-default", TEKST, "tekst op accent-3-vlak"),
    ("basis-color-highlight-inverse-color-default", "basis-color-highlight-bg-default", TEKST, "tekst op highlight"),
    ("basis-color-highlight-color-default", "basis-color-default-bg-default", TEKST, "highlighttekst op paneel"),
]
OPTIONEEL = {
    "basis-color-accent-3-inverse-color-default",
    "basis-color-highlight-inverse-color-default",
    "basis-color-highlight-color-default",
}

# Bekende tekorten in de huidige standaarduitstraling. Het thema d-omnitwin neemt de bestaande kleuren
# één op één over (geen visuele regressie); aanpassen hoort bij de toegankelijkheidsronde (#67).
# legacy (#284) is v0.1.0 zo exact mogelijk: dezelfde tekorten, plus wit op goud (actieve tab) en wit op
# groen (selectiebadge) zoals toen. Beide thema's hebben "@wcag-aa: nee" in de kop.
# Alleen thema's met "@wcag-aa: nee" mogen hier staan; swf (en elk thema met "ja") nooit.
# Een paar dat hier staat maar wél voldoet, laat de test falen: dan moet het van de lijst af.
_TEKORTEN_V010 = {
    ("licht", "basis-color-default-color-subtle", "basis-color-default-bg-document"),
    ("licht", "basis-color-accent-2-bg-default", "basis-color-default-bg-default"),
    # De rand van de actieve tab is (zonder eigen rand) het gouden vlak zelf: hetzelfde tekort als hierboven
    ("licht", "d-omnitwin-tab-active-border-color", "basis-color-default-bg-default"),
    ("donker", "basis-color-accent-1-color-default", "basis-color-default-bg-default"),
    ("donker", "basis-color-accent-1-color-hover", "basis-color-default-bg-default"),
    ("donker", "basis-color-action-1-color-default", "basis-color-default-bg-default"),
    ("donker", "basis-color-negative-color-default", "basis-color-default-bg-default"),
    ("donker", "d-omnitwin-header-color", "d-omnitwin-header-background-color-start"),
    ("donker", "d-omnitwin-header-color", "d-omnitwin-header-background-color-end"),
}
BEKENDE_TEKORTEN = {
    *{("d-omnitwin", *t) for t in _TEKORTEN_V010},
    *{("legacy", *t) for t in _TEKORTEN_V010},
    *{("legacy", modus, voor, achter) for modus in ("licht", "donker") for voor, achter in (
        ("d-omnitwin-tab-active-color", "d-omnitwin-tab-active-background-color"),
        ("d-omnitwin-selection-badge-color", "d-omnitwin-selection-badge-background-color"),
    )},
}

# swf (#284): elk tekstpaar haalt AAA (7:1), behalve deze (wel AA). Reden erbij.
SWF_ALLEEN_AA = {
    # SWF-roze #ff00e3 is te licht voor witte en te donker voor AAA met donkere tekst; de app leest
    # de highlight-tokens nog niet. Met zwart zou het 6,36:1 worden, ook geen AAA.
    "basis-color-highlight-inverse-color-default",
}
WCAG_REGEL = re.compile(r"@wcag-aa:\s*(ja|nee)(?![a-z])")

COMMENTAAR = re.compile(r"/\*.*?\*/", re.S)
DECLARATIE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
BLOK_LICHT = re.compile(r"(?<![\w)-]):root\s*\{([^}]*)\}")
BLOK_DONKER = re.compile(r"(?<![\w-])\[data-theme=\"dark\"\]\s*\{([^}]*)\}")
BLOK_SYSTEEM = re.compile(
    r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme\]\)\s*\{([^}]*)\}\s*\}"
)
HEX = re.compile(r"#[0-9a-fA-F]{6}")
VAR = re.compile(r"var\(--([a-z0-9-]+)(?:,\s*(.+))?\)$")


def declaraties(blok):
    return {naam: waarde.strip() for naam, waarde in DECLARATIE.findall(blok)}


def lees_thema(naam):
    tekst = COMMENTAAR.sub(" ", (THEMA_MAP / f"{naam}.css").read_text(encoding="utf-8"))
    blokken = {}
    for sleutel, patroon in (("licht", BLOK_LICHT), ("donker", BLOK_DONKER), ("systeem", BLOK_SYSTEEM)):
        gevonden = patroon.findall(tekst)
        blokken[sleutel] = [declaraties(b) for b in gevonden]
    return tekst, blokken


def wcag_status(naam):
    """"ja", "nee" of None: de regel "@wcag-aa: ..." in het kopcommentaar van het thema."""
    tekst = (THEMA_MAP / f"{naam}.css").read_text(encoding="utf-8")
    kop = tekst[: tekst.find("*/")] if tekst.lstrip().startswith("/*") else ""
    m = WCAG_REGEL.search(kop)
    return m.group(1) if m else None


def tokens(naam, modus):
    """Tokens van een thema in modus licht/donker; donker erft wat het niet zelf zet van licht."""
    _, blokken = lees_thema(naam)
    waarden = dict(blokken["licht"][0])
    if modus == "donker":
        waarden.update(blokken["donker"][0])
    return waarden


def los_op(waarden, naam, diepte=0):
    """Waarde van een token, met var()-verwijzingen opgelost."""
    if diepte > 10:
        raise ValueError(f"kringverwijzing bij --{naam}")
    waarde = waarden[naam]
    m = VAR.match(waarde)
    if m:
        if m.group(1) in waarden:
            return los_op(waarden, m.group(1), diepte + 1)
        if m.group(2) is not None:
            return m.group(2).strip()
        raise KeyError(f"--{naam} verwijst naar onbekend --{m.group(1)}")
    return waarde


def luminantie(hex_kleur):
    h = hex_kleur.lstrip("#")
    kanalen = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanalen]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((luminantie(a), luminantie(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrasten(naam, modus):
    """[(voorgrond, achtergrond, kleur_v, kleur_a, ratio, minimum, omschrijving)] voor één thema en modus."""
    waarden = tokens(naam, modus)
    uit = []
    for voor, achter, minimum, omschrijving in PAREN:
        if voor not in waarden or achter not in waarden:
            if voor in OPTIONEEL or achter in OPTIONEEL:
                continue
            raise KeyError(f"{naam}/{modus}: token --{voor} of --{achter} ontbreekt")
        kv, ka = los_op(waarden, voor), los_op(waarden, achter)
        uit.append((voor, achter, kv, ka, contrast(kv, ka), minimum, omschrijving))
    return uit


def styles_fallbacks():
    """{modus: {token: fallback}} uit de themablokken van styles.css (var(--token, fallback))."""
    tekst = COMMENTAAR.sub(" ", STYLES.read_text(encoding="utf-8"))
    uit = {"licht": {}, "donker": {}}
    for modus, patroon in (("licht", BLOK_LICHT), ("donker", BLOK_DONKER)):
        for blok in patroon.findall(tekst):
            app = declaraties(blok)
            for waarde in app.values():
                m = VAR.match(waarde)
                if not m or not m.group(1).startswith(("basis-", "d-omnitwin-")):
                    continue
                fallback = m.group(2).strip()
                f = VAR.match(fallback)
                if f:  # bv. --primary-fill: var(--basis-..., var(--primary-color))
                    fallback = VAR.match(app[f.group(1)]).group(2).strip()
                uit[modus][m.group(1)] = fallback
    return uit


def gelijk(a, b):
    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower().replace('"', "'"))  # noqa: E731
    return norm(a) == norm(b)


class TestThemabestanden(unittest.TestCase):
    def test_er_zijn_thema_s(self):
        self.assertIn(STANDAARD_THEMA, beschikbare_themas(THEMA_MAP))
        self.assertIn("swf", beschikbare_themas(THEMA_MAP))

    def test_bestandsnamen_zijn_geldige_themanamen(self):
        for pad in THEMA_MAP.glob("*.css"):
            with self.subTest(bestand=pad.name):
                self.assertTrue(is_geldige_themanaam(pad.stem), f"{pad.name}: alleen [a-z0-9-] in een themanaam")

    def test_opbouw_drie_blokken(self):
        for naam in beschikbare_themas(THEMA_MAP):
            with self.subTest(thema=naam):
                _, blokken = lees_thema(naam)
                for sleutel in ("licht", "donker", "systeem"):
                    self.assertEqual(len(blokken[sleutel]), 1, f"{naam}: precies één {sleutel}-blok verwacht")

    def test_systeem_donker_gelijk_aan_donker(self):
        for naam in beschikbare_themas(THEMA_MAP):
            with self.subTest(thema=naam):
                _, blokken = lees_thema(naam)
                self.assertEqual(blokken["systeem"][0], blokken["donker"][0])

    def test_alleen_thema_tokens_geen_datakleuren(self):
        """Een thema zet alleen --basis-* en --d-omnitwin-*; data- en kaartkleuren horen er niet in."""
        for naam in beschikbare_themas(THEMA_MAP):
            tekst, blokken = lees_thema(naam)
            for sleutel, lijst in blokken.items():
                for blok in lijst:
                    for token in blok:
                        with self.subTest(thema=naam, token=token):
                            self.assertTrue(token.startswith(("basis-", "d-omnitwin-")), token)
            # Geen regels buiten de drie blokken (geen selectors die componenten direct opmaken)
            rest = BLOK_SYSTEEM.sub(" ", tekst)
            rest = BLOK_DONKER.sub(" ", BLOK_LICHT.sub(" ", rest))
            rest = re.sub(r"@import\s+url\([^)]*\)\s*;", " ", rest)
            self.assertEqual(rest.strip(), "", f"{naam}: onverwachte CSS buiten de tokenblokken")

    def test_kleuren_zijn_hex(self):
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                waarden = tokens(naam, modus)
                for token in waarden:
                    if "color" not in token or "font" in token:
                        continue
                    with self.subTest(thema=naam, modus=modus, token=token):
                        self.assertRegex(los_op(waarden, token), r"^#[0-9a-fA-F]{6}$")

    def test_elk_thema_zet_alle_tokens_die_de_app_leest(self):
        fallbacks = styles_fallbacks()
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                waarden = tokens(naam, modus)
                for token in fallbacks[modus]:
                    with self.subTest(thema=naam, modus=modus, token=token):
                        self.assertIn(token, waarden)

    def test_imports_bestaan_en_zijn_lokaal(self):
        for naam in beschikbare_themas(THEMA_MAP):
            tekst = (THEMA_MAP / f"{naam}.css").read_text(encoding="utf-8")
            for url in re.findall(r"@import\s+url\(\"?([^\")]+)\"?\)", tekst):
                with self.subTest(thema=naam, url=url):
                    self.assertNotRegex(url, r"^(https?:)?//")
                    self.assertTrue((THEMA_MAP / url).resolve().is_file(), url)


def gebruikte_componenttokens():
    """{token: {bestand: heeft_terugval}} voor elke var(--d-omnitwin-...) in de viewer."""
    uit = {}
    for pad in VIEWER_BESTANDEN:
        tekst = pad.read_text(encoding="utf-8")
        bestand = pad.relative_to(ROOT).as_posix()
        for naam, teken in re.findall(r"var\(--(d-omnitwin-[a-z0-9-]+)\s*([,)])", tekst):
            per_bestand = uit.setdefault(naam, {})
            # één gebruik zonder terugval in een bestand is genoeg om het als 'zonder' te tellen
            per_bestand[bestand] = per_bestand.get(bestand, True) and teken == ","
    return uit


class TestComponenttokens(unittest.TestCase):
    """Elk --d-omnitwin-token dat de viewer leest, staat in elk thema (licht en donker), en andersom."""

    def test_tokens_zonder_terugval_staan_in_elk_thema(self):
        # Zonder terugvalwaarde wordt de eigenschap ongeldig als het thema het token mist
        gebruikt = gebruikte_componenttokens()
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                waarden = tokens(naam, modus)
                for token, bestanden in gebruikt.items():
                    zonder = [b for b, terugval in bestanden.items() if not terugval]
                    if not zonder:
                        continue
                    with self.subTest(thema=naam, modus=modus, token=token):
                        self.assertIn(token, waarden, f"--{token} (zonder terugval in {', '.join(zonder)}) ontbreekt")

    def test_alle_gebruikte_tokens_staan_in_elk_thema(self):
        # Met terugval werkt de app wel, maar dan geldt het eigen thema stilletjes niet
        gebruikt = gebruikte_componenttokens()
        self.assertGreater(len(gebruikt), 10)
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                waarden = tokens(naam, modus)
                for token in gebruikt:
                    with self.subTest(thema=naam, modus=modus, token=token):
                        self.assertIn(token, waarden)

    def test_thema_zet_geen_onbekende_componenttokens(self):
        # Tikfout in een thema: het token wordt nergens gelezen
        gebruikt = gebruikte_componenttokens()
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                for token in tokens(naam, modus):
                    if token.startswith("d-omnitwin-"):
                        with self.subTest(thema=naam, modus=modus, token=token):
                            self.assertIn(token, gebruikt, f"{naam}: --{token} wordt nergens in de viewer gelezen")


class TestKeycloakInlogthema(unittest.TestCase):
    """Inlogpagina van Keycloak (deploy/keycloak/themes): per viewerthema een inlogthema in dezelfde kleuren."""

    KC = ROOT / "deploy" / "keycloak"

    def test_elk_thema_heeft_een_inlogthema(self):
        for naam in beschikbare_themas(THEMA_MAP):
            with self.subTest(thema=naam):
                props = (self.KC / "themes" / naam / "login" / "theme.properties").read_text(encoding="utf-8")
                self.assertIn("parent=keycloak.v2", props)
                self.assertTrue((self.KC / "themes" / naam / "login" / "resources" / "css" / "omnitwin.css").is_file())

    def test_realm_kiest_een_bestaand_inlogthema(self):
        import json

        realm = json.loads((self.KC / "realm-omnitwin.json").read_text(encoding="utf-8"))
        self.assertIn(realm.get("loginTheme"), beschikbare_themas(THEMA_MAP))

    def test_knopkleur_gelijk_aan_thema(self):
        for naam in beschikbare_themas(THEMA_MAP):
            css = COMMENTAAR.sub(" ", (self.KC / "themes" / naam / "login" / "resources" / "css" / "omnitwin.css").read_text(encoding="utf-8"))
            licht = declaraties(BLOK_LICHT.search(css).group(1))
            with self.subTest(thema=naam):
                self.assertEqual(
                    licht["pf-v5-global--primary-color--100"].lower(),
                    los_op(tokens(naam, "licht"), "basis-color-action-1-bg-default").lower(),
                )


class TestGeenRegressieStandaardthema(unittest.TestCase):
    def test_d_omnitwin_gelijk_aan_fallbacks_in_styles(self):
        fallbacks = styles_fallbacks()
        self.assertGreater(len(fallbacks["licht"]), 20)
        for modus in ("licht", "donker"):
            waarden = tokens(STANDAARD_THEMA, modus)
            for token, fallback in fallbacks[modus].items():
                with self.subTest(modus=modus, token=token):
                    self.assertTrue(
                        gelijk(los_op(waarden, token), fallback),
                        f"--{token}: thema {los_op(waarden, token)!r}, styles.css {fallback!r}",
                    )

    def test_d_omnitwin_gelijk_aan_fallbacks_in_beheerscherm(self):
        """De --d-omnitwin-*-tokens in admin.css (#284): het standaardthema verandert het beheerscherm niet."""
        tekst = COMMENTAAR.sub(" ", ADMIN_CSS.read_text(encoding="utf-8"))
        gevonden = re.findall(r"var\(--(d-omnitwin-[a-z0-9-]+),\s*([^)]+)\)", tekst)
        self.assertGreaterEqual(len(gevonden), 5)
        donker = tokens(STANDAARD_THEMA, "donker")  # het beheerscherm is altijd donker
        for token, terugval in gevonden:
            with self.subTest(token=token):
                self.assertTrue(gelijk(los_op(donker, token), terugval), f"--{token}: {los_op(donker, token)} != {terugval}")

    def test_lettertypen_standaard_gelijk(self):
        tekst = STYLES.read_text(encoding="utf-8")
        m = re.search(r"font-family:\s*var\(--basis-text-font-family-default,\s*([^;]+)\);", tekst)
        self.assertIsNotNone(m)
        self.assertTrue(gelijk(tokens(STANDAARD_THEMA, "licht")["basis-text-font-family-default"], m.group(1)))


class TestContrast(unittest.TestCase):
    """WCAG 2.1 AA: 4,5:1 voor tekst, 3:1 voor UI-onderdelen en focus."""

    def test_wcag_aa(self):
        for naam in beschikbare_themas(THEMA_MAP):
            for modus in ("licht", "donker"):
                for voor, achter, kv, ka, ratio, minimum, omschrijving in contrasten(naam, modus):
                    bekend = (naam, modus, voor, achter) in BEKENDE_TEKORTEN
                    with self.subTest(thema=naam, modus=modus, paar=omschrijving):
                        if bekend:
                            self.assertLess(ratio, minimum, f"{omschrijving} voldoet nu ({ratio:.2f}); haal van BEKENDE_TEKORTEN")
                        else:
                            self.assertGreaterEqual(
                                round(ratio, 2), minimum, f"{omschrijving}: {kv} op {ka} = {ratio:.2f}:1 < {minimum}:1"
                            )

    def test_swf_heeft_geen_tekorten(self):
        self.assertFalse([t for t in BEKENDE_TEKORTEN if t[0] == "swf"])

    def test_swf_tekst_aaa(self):
        """swf (#284): tekst 7:1 (AAA), op de gedocumenteerde uitzonderingen na; UI en focus 3:1 (AA)."""
        for modus in ("licht", "donker"):
            for voor, achter, kv, ka, ratio, minimum, omschrijving in contrasten("swf", modus):
                if minimum != TEKST or voor in SWF_ALLEEN_AA:
                    continue
                with self.subTest(modus=modus, paar=omschrijving):
                    self.assertGreaterEqual(round(ratio, 2), AAA, f"{omschrijving}: {kv} op {ka} = {ratio:.2f}:1 < 7:1")

    def test_swf_actieve_tab_niet_alleen_kleur(self):
        """WCAG 1.4.1: de actieve tab heeft een dikkere rand dan gewone tabs (2px), niet alleen een andere kleur."""
        breedte = tokens("swf", "licht")["d-omnitwin-tab-active-border-width"]
        self.assertGreater(float(breedte.removesuffix("px")), 2)


class TestWcagStatus(unittest.TestCase):
    """"@wcag-aa: ja|nee" in de kop van elk thema (#284): klopt met de contrasten en staat in het beheerscherm."""

    def test_elk_thema_heeft_de_regel(self):
        for naam in beschikbare_themas(THEMA_MAP):
            with self.subTest(thema=naam):
                self.assertIn(wcag_status(naam), ("ja", "nee"))

    def test_regel_klopt_met_contrasten(self):
        for naam in beschikbare_themas(THEMA_MAP):
            tekorten = [
                (modus, voor, achter)
                for modus in ("licht", "donker")
                for voor, achter, _, _, ratio, minimum, _ in contrasten(naam, modus)
                if round(ratio, 2) < minimum
            ]
            with self.subTest(thema=naam):
                if wcag_status(naam) == "ja":
                    self.assertEqual(tekorten, [], f"{naam} zegt '@wcag-aa: ja' maar haalt AA niet")
                    self.assertFalse([t for t in BEKENDE_TEKORTEN if t[0] == naam])
                else:
                    self.assertTrue(tekorten, f"{naam} haalt AA: zet '@wcag-aa: ja' in de kop")

    def test_legacy_en_swf(self):
        self.assertEqual(wcag_status("legacy"), "nee")
        self.assertEqual(wcag_status("swf"), "ja")


    def test_beheermodus(self):
        """Standaardweergave van het beheerscherm (#284): swf licht zoals de site, de rest donker zoals het was."""
        for naam in beschikbare_themas(THEMA_MAP):
            with self.subTest(thema=naam):
                self.assertIn(tokens(naam, "licht")["d-omnitwin-beheer-modus"], ("licht", "donker"))
        self.assertEqual(tokens("swf", "licht")["d-omnitwin-beheer-modus"], "licht")
        self.assertEqual(tokens("d-omnitwin", "licht")["d-omnitwin-beheer-modus"], "donker")
        self.assertEqual(tokens("legacy", "licht")["d-omnitwin-beheer-modus"], "donker")


class TestLegacyNooitStandaard(unittest.TestCase):
    """legacy (#284) haalt WCAG AA niet: nooit de standaard, niet in de code en niet in de vulling."""

    def test_niet_de_standaard_in_code(self):
        self.assertNotEqual(STANDAARD_THEMA, "legacy")
        service = (ROOT / "src" / "omnitwin" / "services" / "organisatie.py").read_text(encoding="utf-8")
        self.assertRegex(service, r'STANDAARD_THEMA = "d-omnitwin"')

    def test_niet_in_organisatie_vulling(self):
        sql = (ROOT / "db" / "stuurdata" / "organisatie.sql").read_text(encoding="utf-8")
        sql = re.sub(r"--[^\n]*", " ", sql)
        self.assertNotIn("'legacy'", sql)

    def test_niet_het_inlogthema_van_de_realm(self):
        import json

        realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-omnitwin.json").read_text(encoding="utf-8"))
        self.assertNotEqual(realm.get("loginTheme"), "legacy")
        self.assertEqual(wcag_status(realm.get("loginTheme")), "ja", "de realm kiest standaard een WCAG-AA-thema")

    def test_legacy_is_v010(self):
        """Kopbalk en knoppen zoals static/css/styles.css in v0.1.0."""
        licht, donker = tokens("legacy", "licht"), tokens("legacy", "donker")
        self.assertEqual(los_op(licht, "d-omnitwin-header-background-color-start"), "#1e3a8a")
        self.assertEqual(licht["d-omnitwin-header-background-color-end"], "#15803d")
        self.assertEqual(donker["d-omnitwin-header-background-color-start"], "#3b82f6")
        self.assertEqual(donker["d-omnitwin-header-background-color-end"], "#22c55e")
        self.assertEqual(licht["basis-color-action-1-bg-default"], "#1e3a8a")
        self.assertEqual(licht["d-omnitwin-tab-active-color"], "#ffffff")
        self.assertEqual(licht["d-omnitwin-header-accent-width"], "0px")

    def test_contrastberekening(self):
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(contrast("#ffffff", "#bf0042"), 6.38, places=2)
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), 4.54, places=2)


class TestThemanaam(unittest.TestCase):
    def test_geldige_namen(self):
        for naam in ("d-omnitwin", "swf", "leeuwarden", "gemeente-2026", "a"):
            with self.subTest(naam=naam):
                self.assertTrue(is_geldige_themanaam(naam))

    def test_ongeldige_namen(self):
        for naam in ("", "SWF", "swf.css", "../swf", "swf/x", "swf x", "-swf", "swf-", "a--b", "swf_1",
                     "swéf", "x" * 65, None, 3, ["swf"]):
            with self.subTest(naam=naam):
                self.assertFalse(is_geldige_themanaam(naam))

    def test_kies_thema_valt_terug_op_standaard(self):
        self.assertEqual(kies_thema("swf", THEMA_MAP), "swf")
        self.assertEqual(kies_thema("d-omnitwin", THEMA_MAP), "d-omnitwin")
        for naam in (None, "", "../../templates/index", "SWF", "bestaat-niet"):
            with self.subTest(naam=naam):
                self.assertEqual(kies_thema(naam, THEMA_MAP), STANDAARD_THEMA)

    def test_kies_thema_negeert_ongeldige_bestandsnaam(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Fout_Naam.css").write_text(":root{}", encoding="utf-8")
            (Path(tmp) / "goed.css").write_text(":root{}", encoding="utf-8")
            self.assertEqual(beschikbare_themas(Path(tmp)), ["goed"])
            self.assertEqual(kies_thema("Fout_Naam", Path(tmp)), STANDAARD_THEMA)


def rapport():
    """Contrasttabel per thema en modus (Markdown)."""
    regels = []
    for naam in beschikbare_themas(THEMA_MAP):
        for modus in ("licht", "donker"):
            regels.append(f"\n### {naam} — {modus} (@wcag-aa: {wcag_status(naam)})\n\n| Paar | Voorgrond | Achtergrond | Contrast | Eis | |\n|---|---|---|---|---|---|")
            for voor, achter, kv, ka, ratio, minimum, omschrijving in contrasten(naam, modus):
                bekend = (naam, modus, voor, achter) in BEKENDE_TEKORTEN
                teken = "ok" if round(ratio, 2) >= minimum else ("bekend tekort (#67)" if bekend else "FOUT")
                if teken == "ok" and minimum == TEKST and round(ratio, 2) >= AAA:
                    teken = "ok (AAA)"
                regels.append(f"| {omschrijving} | `{kv}` | `{ka}` | {ratio:.2f}:1 | {minimum}:1 | {teken} |")
    return "\n".join(regels)


if __name__ == "__main__":
    if "--rapport" in sys.argv:
        print(rapport())
    else:
        unittest.main()
