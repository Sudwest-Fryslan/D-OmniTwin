"""
De eigen organisatie van deze instantie, als data (#231, ADR 0007).

Eén D-OmniTwin-instantie hoort bij één organisatie. Naam, gemeentecode(s) van het
eigen gebied, standaard-benchmarkgebied, contactpunt en logo's staan in de tabel
``organisatie`` (vulling: ``db/stuurdata/organisatie.sql``), niet in de code.

Regel: code die "de eigen gemeente" nodig heeft, vraagt die hier op
(``eigen_gemeente_code``) en neemt nooit een vaste code aan.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from omnitwin.services.logging_service import AppLogger
from omnitwin.thema import beschikbare_themas, is_geldige_themanaam

STANDAARD_THEMA = "d-omnitwin"
_THEMA = re.compile(r"^[a-z0-9-]+$")
THEMA_MAP = Path(__file__).resolve().parents[3] / "static" / "css" / "themes"


def veilig_thema(thema: Optional[str]) -> str:
    """Themanaam alleen met [a-z0-9-]; anders het standaardthema."""
    return thema if isinstance(thema, str) and _THEMA.fullmatch(thema) else STANDAARD_THEMA


BEELDMERK = THEMA_MAP.parents[1] / "images" / "beeldmerk.svg"
_BEELDMERK_TOKEN = re.compile(r"var\(--d-omnitwin-beeldmerk-(vlak|lijn|kern),\s*(#[0-9A-Fa-f]{3,8})\)")
_KLEUR = re.compile(r"^#[0-9A-Fa-f]{3,8}$")


def beeldmerk_kleuren(thema: str, themamap: Path = THEMA_MAP) -> Dict[str, str]:
    """Kleuren --d-omnitwin-beeldmerk-{vlak,lijn,kern} uit het eerste (lichte) :root-blok van het thema."""
    pad = themamap / f"{veilig_thema(thema)}.css"
    if not pad.is_file():
        return {}
    css = pad.read_text(encoding="utf-8")
    start = css.find(":root")
    blok = css[start:css.find("}", start)] if start >= 0 else ""
    kleuren = {}
    for deel in ("vlak", "lijn", "kern"):
        m = re.search(rf"--d-omnitwin-beeldmerk-{deel}:\s*([^;]+);", blok)
        if m and _KLEUR.match(m.group(1).strip()):
            kleuren[deel] = m.group(1).strip()
    return kleuren


def beeldmerk_svg(org: Optional[Dict[str, Any]], svg: Path = BEELDMERK, themamap: Path = THEMA_MAP) -> str:
    """Het beeldmerk met de themakleuren als vaste waarden, voor favicons (#249).

    Een favicon kan geen CSS-variabelen van de pagina lezen; daarom vervangen we de
    terugvalwaarden in ``var(--d-omnitwin-beeldmerk-*, #...)`` door de kleuren van het thema.
    Een eigen logo zonder die tokens komt ongewijzigd terug."""
    kleuren = beeldmerk_kleuren(veilig_thema(org.get("thema") if org else None), themamap)
    tekst = svg.read_text(encoding="utf-8")
    return _BEELDMERK_TOKEN.sub(
        lambda m: f"var(--d-omnitwin-beeldmerk-{m.group(1)}, {kleuren.get(m.group(1), m.group(2))})", tekst)


def thema_css(org: Optional[Dict[str, Any]], themamap: Path = THEMA_MAP) -> Optional[str]:
    """URL van static/css/themes/<thema>.css als dat bestand bestaat, anders None."""
    thema = veilig_thema(org.get("thema") if org else None)
    return f"/static/css/themes/{thema}.css" if (themamap / f"{thema}.css").is_file() else None


# ── Instellen vanuit het beheerscherm (#253) ─────────────────────────────────

AFBEELDINGEN = THEMA_MAP.parents[1] / "images"
LOGO_PREFIX = "/static/images/"
LOGO_EXTENSIES = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
_DONKER = '[data-theme="dark"]'
_TOKEN = re.compile(r"(--(?:basis|d-omnitwin)-[a-z0-9-]+):\s*([^;]+);")
_VAR = re.compile(r"^var\(\s*(--[a-z0-9-]+)\s*(?:,\s*(.+))?\)$")
# Kopcommentaar: Thema "swf" — Gemeente Súdwest-Fryslân, als ... -> "Gemeente Súdwest-Fryslân"
# Kopcommentaar: "@wcag-aa: ja" of "@wcag-aa: nee" (#284); tests/test_thema.py houdt het eerlijk
_WCAG_AA = re.compile(r"@wcag-aa:\s*(ja|nee)(?![a-z])")
_TITEL = re.compile(r'Thema\s+"[a-z0-9-]+"\s+[—-]+\s*([^,.\n(]+?)(?:\s+als NL Design System|[,.\n(])')


def _blok(css: str, selector: str) -> str:
    """De inhoud van het eerste blok met precies deze selector (zonder geneste blokken)."""
    start = css.find(selector + " {")
    if start < 0:
        return ""
    open_ = css.find("{", start)
    return css[open_ + 1:css.find("}", open_)]


def _kleuren(tokens: Dict[str, str]) -> Dict[str, str]:
    """Alleen de tokens met een kleur (#hex), met ``var(--ander)`` opgelost binnen dezelfde set."""
    def los_op(waarde: str, diepte: int = 0) -> Optional[str]:
        waarde = waarde.strip()
        if _KLEUR.match(waarde):
            return waarde
        m = _VAR.match(waarde)
        if not m or diepte > 5:
            return None
        if m.group(1) in tokens:
            return los_op(tokens[m.group(1)], diepte + 1)
        return los_op(m.group(2), diepte + 1) if m.group(2) else None

    return {naam: kleur for naam, waarde in tokens.items() if (kleur := los_op(waarde))}


def thema_bestaat(naam: object, themamap: Path = THEMA_MAP) -> bool:
    return is_geldige_themanaam(naam) and (themamap / f"{naam}.css").is_file()


def thema_info(naam: str, themamap: Path = THEMA_MAP) -> Dict[str, Any]:
    """Naam, titel, WCAG-status (uit het kopcommentaar) en kleurtokens van een thema, licht en donker.

    ``wcag_aa``: True/False volgens de regel ``@wcag-aa: ja|nee`` in het kopcommentaar, None als die
    ontbreekt (onbekend; een eigen thema zonder die regel is niet getoetst).

    Licht = het eerste ``:root``-blok, donker = ``[data-theme="dark"]`` aangevuld met licht
    (zoals de cascade in de browser: wat donker niet zet, komt uit :root)."""
    css = (themamap / f"{naam}.css").read_text(encoding="utf-8")
    m = _TITEL.search(css[:600])
    kop = css[:css.find("*/")] if css.lstrip().startswith("/*") else ""
    wcag = _WCAG_AA.search(kop)
    licht = dict(_TOKEN.findall(_blok(css, ":root")))
    donker = {**licht, **dict(_TOKEN.findall(_blok(css, _DONKER)))}
    return {"naam": naam, "titel": m.group(1).strip() if m else naam,
            "wcag_aa": (wcag.group(1) == "ja") if wcag else None,
            "kleuren": {"licht": _kleuren(licht), "donker": _kleuren(donker)}}


def themas(themamap: Path = THEMA_MAP) -> List[Dict[str, Any]]:
    """Alle themabestanden in static/css/themes met titel en voorbeeldkleuren."""
    return [thema_info(n, themamap) for n in beschikbare_themas(themamap)]


def logo_bestand(pad: object, afbeeldingen: Path = AFBEELDINGEN) -> Optional[Path]:
    """Het bestand achter een logopad, alleen als het een bestaande afbeelding onder
    /static/images/ is (geen ``..``, geen andere map, geen uploads); anders None."""
    if not isinstance(pad, str) or not pad.startswith(LOGO_PREFIX) or len(pad) > 300:
        return None
    rel = pad[len(LOGO_PREFIX):]
    if not rel or "\\" in rel or any(d in ("", ".", "..") for d in rel.split("/")):
        return None
    bestand = (afbeeldingen / rel).resolve()
    basis = afbeeldingen.resolve()
    if basis not in bestand.parents or bestand.suffix.lower() not in LOGO_EXTENSIES or not bestand.is_file():
        return None
    return bestand


def beschikbare_logos(afbeeldingen: Path = AFBEELDINGEN) -> List[str]:
    """Paden (``/static/images/...``) van de afbeeldingen die als logo gekozen kunnen worden."""
    return sorted(
        LOGO_PREFIX + p.relative_to(afbeeldingen).as_posix()
        for p in afbeeldingen.rglob("*")
        if p.is_file() and p.suffix.lower() in LOGO_EXTENSIES
    )


_VELDEN = ("code", "naam", "korte_naam", "oin", "gemeente_codes", "benchmark_provincie",
           "contact_email", "thema", "logos", "meld_url")

# Meldplek als de instantie geen eigen meld_url heeft (#312): een nieuw issue bij D-OmniTwin zelf
STANDAARD_MELD_URL = "https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/new"


def wijzigingen(oud: Optional[Dict[str, Any]], nieuw: Dict[str, Any]) -> Dict[str, Any]:
    """Wat er verandert, voor de auditlog: {veld: {"oud": ..., "nieuw": ...}}.

    Het contactadres alleen als "gewijzigd" (geen adressen in de log, #264)."""
    oud = oud or {}
    uit: Dict[str, Any] = {}
    for veld in _VELDEN:
        a, b = oud.get(veld), nieuw.get(veld)
        if veld == "logos":
            a = [l.get("pad") for l in (a or [])]
            b = [l.get("pad") for l in (b or [])]
            if a == b and [(l.get("naam"), l.get("rol")) for l in (oud.get("logos") or [])] !=                     [(l.get("naam"), l.get("rol")) for l in (nieuw.get("logos") or [])]:
                uit[veld] = "namen of rollen gewijzigd"
                continue
        if a != b:
            uit[veld] = "gewijzigd" if veld == "contact_email" else {"oud": a, "nieuw": b}
    return uit


_SCHRIJF = text("""
    INSERT INTO public.organisatie
        (id, code, naam, korte_naam, oin, gemeente_codes, benchmark_provincie, contact_email, thema, logos,
         meld_url, bijgewerkt_op)
    VALUES (true, :code, :naam, :korte_naam, :oin, :gemeente_codes, :benchmark_provincie, :contact_email,
            :thema, CAST(:logos AS jsonb), :meld_url, now())
    ON CONFLICT (id) DO UPDATE SET
        code = EXCLUDED.code, naam = EXCLUDED.naam, korte_naam = EXCLUDED.korte_naam, oin = EXCLUDED.oin,
        gemeente_codes = EXCLUDED.gemeente_codes, benchmark_provincie = EXCLUDED.benchmark_provincie,
        contact_email = EXCLUDED.contact_email, thema = EXCLUDED.thema, logos = EXCLUDED.logos,
        meld_url = EXCLUDED.meld_url, bijgewerkt_op = now()
""")


def schrijf_organisatie(db: Session, org: Dict[str, Any]) -> None:
    """Zet de (enige) rij van de organisatie; de invoer is al gevalideerd (router)."""
    params = {veld: org.get(veld) for veld in _VELDEN}
    params["gemeente_codes"] = list(org.get("gemeente_codes") or [])
    params["logos"] = json.dumps([{"pad": l["pad"], "naam": l.get("naam"), "rol": l.get("rol", "partner")}
                                  for l in org.get("logos") or []], ensure_ascii=False)
    db.execute(_SCHRIJF, params)
    db.commit()


_SQL = text("""
    SELECT code, naam, korte_naam, oin, gemeente_codes, benchmark_provincie,
           contact_email, logos, thema, meld_url
    FROM public.organisatie
    LIMIT 1
""")


def _als_dict(rij) -> Dict[str, Any]:
    m = dict(rij._mapping)
    codes: List[str] = [str(c) for c in (m.get("gemeente_codes") or [])]
    logos = m.get("logos") or []
    return {
        "code": m["code"],
        "naam": m["naam"],
        "korte_naam": m.get("korte_naam"),
        "oin": m.get("oin"),
        "gemeente_codes": codes,
        "standaard_gemeente_code": codes[0] if codes else None,
        "benchmark_provincie": m.get("benchmark_provincie"),
        "contact_email": m.get("contact_email"),
        "thema": veilig_thema(m.get("thema")),
        # Leeg = de standaard; viewer en beheer krijgen altijd een bruikbare meldplek (#312)
        "meld_url": m.get("meld_url") or STANDAARD_MELD_URL,
        "logos": [
            {"pad": l.get("pad"), "naam": l.get("naam"), "rol": l.get("rol", "partner")}
            for l in logos
            if isinstance(l, dict) and l.get("pad")
        ],
    }


def lees_organisatie(db: Session) -> Optional[Dict[str, Any]]:
    """De organisatie van deze instantie, of None als die (nog) niet is ingericht.

    Een database zonder de tabel (migratie V027 nog niet toegepast) geeft ook None.
    """
    try:
        rij = db.execute(_SQL).fetchone()
    except SQLAlchemyError as e:
        db.rollback()
        AppLogger.warning(f"Organisatie niet te lezen: {e.__class__.__name__}", category="SERVER")
        return None
    return _als_dict(rij) if rij else None


def eigen_gemeente_code(db: Session) -> Optional[str]:
    """De standaard-gemeentecode van de eigen organisatie (de eerste uit gemeente_codes)."""
    org = lees_organisatie(db)
    return org["standaard_gemeente_code"] if org else None
