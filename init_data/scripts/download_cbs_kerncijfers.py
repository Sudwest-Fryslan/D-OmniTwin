#!/usr/bin/env python3
"""
CBS Kerncijfers wijken en buurten, alle jaargangen, voor alle buurten in Fryslân
================================================================================
Haalt via CBS OData (opendata.cbs.nl) de Kerncijfers wijken en buurten op van
2019 t/m de nieuwste jaargang. **De data staat niet in git**: wat bij CBS te downloaden is,
downloaden we op het moment dat het nodig is (bij het laden van een use case) naar een cache:

    $DATA_CACHE/cbs/kerncijfers_<gebieden>.csv   (standaard ./data-cache, in Docker het volume bron-cache)

In git staat alleen het recept: tabel-ID's per jaar, de kolom-mapping, licentie en de
codecontrole (init_data/cbs/datapackage.json, bijgewerkt met --alle).

Uitgangspunten (#159):
- jaar = het echte peiljaar van de tabel (TableInfos.Period), gecontroleerd bij elke download;
- één mapping CBS-kolom -> D-OmniTwin-indicator, per jaar (kolomnamen verschillen per jaar);
- dezelfde indicator-UUID's als de sample: meerdere jaren, geen dubbele indicatoren;
- percentages zoals CBS ze geeft; afgeleid (65+ jaar (%)) alleen uit hetzelfde jaar;
- alleen buurtcodes die in de geometrie van 2024 bestaan (init_data/fryslan/buurten_fryslan.geojson);
  wat wegvalt staat per jaar en gemeente in datapackage.json.

Laden: init_data/scripts/laad_cbs.py (gebruikt download() hieronder, met cache).

Gebruik:
    python init_data/scripts/download_cbs_kerncijfers.py --controle   # tabellen (Period) en kolommen controleren
    python init_data/scripts/download_cbs_kerncijfers.py --alle       # heel Fryslân naar de cache + datapackage.json bijwerken
    python init_data/scripts/download_cbs_kerncijfers.py BU19000001 ...  # alleen deze buurten naar de cache

Licentie van de data: CC BY 4.0, bron: Centraal Bureau voor de Statistiek (CBS).
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UIT_DIR = ROOT / "init_data" / "cbs"
UIT_PACKAGE = UIT_DIR / "datapackage.json"
CACHE_DIR = Path(os.environ.get("DATA_CACHE", ROOT / "data-cache")) / "cbs"
GEOMETRIE = ROOT / "init_data" / "fryslan" / "buurten_fryslan.geojson"
# Eén bron voor de jaargang van de buurtgeometrie (#159): download_buurten_fryslan.py gebruikt deze,
# en tests/test_cbs_kerncijfers.py controleert de sample, het recept en de use case cbs-gebiedsindelingen.
GEOMETRIE_JAAR = 2024
# Waarden van buurtcodes die niet in de geometrie bestaan, vallen weg. Boven dit aandeel per jaargang
# stopt de download (#159): dan is er een nieuwe herindeling of klopt de geometrie niet.
# Nu: hoogstens 3,6% (Smallingerland, herindeling 2024; zie codecontrole in datapackage.json).
MAX_WEGGEVALLEN = 0.05

CBS_API = "https://opendata.cbs.nl/ODataApi/odata"
LICENTIE = "CC BY 4.0"

# Peiljaar -> CBS-tabel "Kerncijfers wijken en buurten <jaar>". Gecontroleerd via TableInfos.Period.
TABELLEN = {
    2019: "84583NED",
    2020: "84799NED",
    2021: "85039NED",
    2022: "85318NED",
    2023: "85618NED",
    2024: "85984NED",
    2025: "86165NED",
    2026: "86358NED",
}

FRIESE_GM_CODES = [
    "0059",
    "0060",
    "1891",
    "1940",
    "0072",
    "0074",
    "0080",
    "1970",
    "0085",
    "0086",
    "0088",
    "0090",
    "1900",
    "0093",
    "0737",
    "0096",
    "1949",
    "0098",
]

# Indicatoren van D-OmniTwin (namen en UUID's uit init_data/sample/2_brondata/sample_indicatoren.csv):
# naam -> (uuid, eenheid, interpretatie_logica, categorie). Leeftijdsgroepen zijn neutraal: geen oordeel (#236).
INDICATOREN = {
    "Inwoners": ("31f70dff-c116-4267-bef0-d15b0ff4c020", "aantal", "pos_is_pos", ""),
    "0-15 jaar": ("356a2329-eadb-494f-a09d-906a3db264d4", "Aantal", "neutraal", ""),
    "15-25 jaar": ("026bcd11-ace5-4ec7-adbc-c06c324315cd", "Aantal", "neutraal", ""),
    "25-45 jaar": ("e6dd31a1-a056-4c07-a48c-1d4517269f1e", "Aantal", "neutraal", ""),
    "45-65 jaar": ("8225fa5c-efb8-4fd0-865b-a36ff0724a28", "Aantal", "neutraal", ""),
    "65+ jaar": ("b0ee9877-3850-4529-b352-6ec673562ef8", "Aantal", "neutraal", ""),
    # Nieuw in 2026 (k_80JaarOfOuder_13); hittestress gebruikt het percentage (#236)
    "80 jaar of ouder": ("debc6665-b839-54dc-bd7e-4f9a749e2883", "aantal", "neutraal", ""),
    "Huishoudens totaal": ("be1a9ac4-6330-47c9-93c6-c9008b5daf89", "aantal", "pos_is_pos", ""),
    "Eenpersoonshuishoudens": ("257494f4-9e51-4a4a-a662-feabfe9758b0", "aantal", "pos_is_pos", ""),
    "Huishoudens zonder kind": ("428c1232-0213-491b-ad0c-56dcc82a8c59", "aantal", "pos_is_pos", ""),
    "Huishoudens met kind": ("ad3b0509-3c14-49f8-aa10-4b3b391a2d84", "aantal", "pos_is_pos", ""),
    "Bevolkingsdichtheid": ("f18b2c78-871b-48a7-b08f-fa743e589db8", "inw/km²", "pos_is_pos", ""),
    "Woningvoorraad": ("e3d59c6a-adf9-4bad-b842-98ce71760935", "aantal", "pos_is_pos", ""),
    "Gemiddelde WOZ-waarde": ("7053d6a5-2bcf-4254-b089-79852f12d9aa", "x 1 000 euro", "pos_is_pos", ""),
    "Koopwoningen": ("a0bbfd44-bacd-4434-bc8d-3a5204d65637", "percentage", "pos_is_pos", ""),
    "Woningcorporatie bezit": ("6dd8b659-29c1-4396-a853-1abd7c6e0591", "%", "pos_is_pos", ""),
    "Particulier huurbezit": ("2aadb30f-860f-4f70-916f-6df00e86e870", "%", "pos_is_pos", ""),
    "Netto arbeidsparticipatie": ("b07f74eb-5117-4705-802c-597ba830d016", "%", "pos_is_pos", ""),
    "Percentage werknemers": ("352dda4d-5de8-4f31-b85a-6d82f812ba7c", "percentage", "pos_is_pos", "Gebruik"),
    "Percentage zelfstandigen": ("f8d0d890-3975-4183-9555-06d673c4657f", "percentage", "pos_is_pos", "Gebruik"),
    "Inkomen per inwoner": ("9c035f53-75a5-43eb-8496-22c4c6f08d6b", "x 1 000 euro", "pos_is_pos", ""),
    "Huishoudens met laag inkomen": ("3dd70913-391e-4d5f-a121-d17c8b466372", "%", "-/+", ""),
    "Opleidingsniveau laag": ("c9719a07-57a5-48cf-8f93-b6f932aead51", "aantal", "pos_is_pos", ""),
    "Opleidingsniveau middelbaar": ("1fa5df89-13e3-424f-9eba-9372cae42896", "aantal", "pos_is_pos", ""),
    "Opleidingsniveau hoog": ("56f32b9a-bc45-4be1-9e1c-c2668c2e2a32", "aantal", "pos_is_pos", ""),
    "Participatiewet totaal": ("aa5ce990-a43e-439a-9e98-69899321cf40", "aantal", "-/+", ""),
    "Personenauto's per huishouden": ("461d542b-b8be-4510-9dd0-5ba554b818cb", "per huishouden", "pos_is_pos", ""),
    "Personenauto's naar oppervlakte": ("88192b70-faa9-4108-a473-302aa0f624a9", "per km²", "pos_is_pos", ""),
    "Afstand tot huisarts": ("1b28d9ef-f7ff-4609-9ef7-7ab8a9b6cba7", "km", "-/+", ""),
    "Afstand tot grote supermarkt": ("869bec9c-9b9a-4425-9cd6-09cb4f7451ae", "km", "-/+", ""),
    "Afstand tot kinderdagverblijf": ("76abbf47-6eb6-4c10-a4bf-ec0280435052", "km", "-/+", ""),
    "Afstand tot school": ("ec95fe04-04fd-4bbb-bb9f-0f3f97861e5d", "km", "-/+", ""),
}

# Afgeleid, alleen uit hetzelfde jaar. UUID gelijk aan die van laad_usecase.py (uuid5 op de naam),
# zodat de use case en dit pakket dezelfde indicator vullen.
_NAMESPACE_AFGELEID = uuid.UUID("6f1d3c2a-0b7e-4c8e-9a51-d0a1b2c3e4f5")
AFGELEID = {
    "65+ jaar (%)": {"teller": "65+ jaar", "noemer": "Inwoners", "factor": 100, "eenheid": "%", "logica": "neutraal"},
    "Eenpersoonshuishoudens (%)": {
        "teller": "Eenpersoonshuishoudens",
        "noemer": "Huishoudens totaal",
        "factor": 100,
        "eenheid": "%",
    },
    "80 jaar of ouder (%)": {
        "teller": "80 jaar of ouder",
        "noemer": "Inwoners",
        "factor": 100,
        "eenheid": "%",
        "logica": "neutraal",
    },
}
for _naam, _a in AFGELEID.items():
    INDICATOREN[_naam] = (
        str(uuid.uuid5(_NAMESPACE_AFGELEID, _naam)),
        _a["eenheid"],
        _a.get("logica", "pos_is_pos"),
        "",
    )


def _reeks(stam, n2019, n2020, n2021, n2022, n2023, n2024, n2025, n2026):
    """Kolom per jaar voor een CBS-stam met wisselend volgnummer; None = niet in die tabel."""
    nummers = dict(zip(TABELLEN, [n2019, n2020, n2021, n2022, n2023, n2024, n2025, n2026]))
    return {j: f"{stam}_{n}" for j, n in nummers.items() if n is not None}


# DE mapping: indicator -> {peiljaar: CBS-kolom}. Een tuple betekent: som van kolommen uit dezelfde tabel.
# Jaren zonder kolom ontbreken bewust (CBS publiceert de variabele dan niet).
MAPPING = {
    "Inwoners": _reeks("AantalInwoners", 5, 5, 5, 5, 5, 5, 5, 5),
    "0-15 jaar": _reeks("k_0Tot15Jaar", 8, 8, 8, 8, 8, 8, 8, 8),
    "15-25 jaar": _reeks("k_15Tot25Jaar", 9, 9, 9, 9, 9, 9, 9, 9),
    "25-45 jaar": _reeks("k_25Tot45Jaar", 10, 10, 10, 10, 10, 10, 10, 10),
    "45-65 jaar": _reeks("k_45Tot65Jaar", 11, 11, 11, 11, 11, 11, 11, 11),
    # 2026 splitst 65+ in 65-80 en 80+: som uit dezelfde tabel
    "65+ jaar": {
        **_reeks("k_65JaarOfOuder", 12, 12, 12, 12, 12, 12, 12, None),
        2026: ("k_65JaarTot80Jaar_12", "k_80JaarOfOuder_13"),
    },
    "80 jaar of ouder": {2026: "k_80JaarOfOuder_13"},
    "Huishoudens totaal": _reeks("HuishoudensTotaal", 28, 28, 28, 28, 29, 29, 29, 30),
    "Eenpersoonshuishoudens": _reeks("Eenpersoonshuishoudens", 29, 29, 29, 29, 30, 30, 30, 31),
    "Huishoudens zonder kind": _reeks("HuishoudensZonderKinderen", 30, 30, 30, 30, 31, 31, 31, 32),
    "Huishoudens met kind": _reeks("HuishoudensMetKinderen", 31, 31, 31, 31, 32, 32, 32, 33),
    "Bevolkingsdichtheid": _reeks("Bevolkingsdichtheid", 33, 33, 33, 33, 34, 34, 34, 35),
    "Woningvoorraad": _reeks("Woningvoorraad", 34, 34, 34, 34, 35, 35, 35, 36),
    "Gemiddelde WOZ-waarde": _reeks("GemiddeldeWOZWaardeVanWoningen", 35, 35, 35, 35, 36, 39, 39, 40),
    "Koopwoningen": _reeks("Koopwoningen", 40, 40, 40, 40, 41, 47, 47, 48),
    "Woningcorporatie bezit": _reeks("InBezitWoningcorporatie", 42, 42, 42, 42, 43, 49, 49, 50),
    "Particulier huurbezit": _reeks("InBezitOverigeVerhuurders", 43, 43, 43, 43, 44, 50, 50, 51),
    "Netto arbeidsparticipatie": _reeks("Nettoarbeidsparticipatie", 67, 67, 67, 67, 74, 71, 71, 72),
    "Percentage werknemers": _reeks("PercentageWerknemers", 68, 68, 68, 68, 75, 72, 72, 73),
    "Percentage zelfstandigen": _reeks("PercentageZelfstandigen", 69, 69, 69, 69, 78, 75, 75, 76),
    "Inkomen per inwoner": _reeks("GemiddeldInkomenPerInwoner", 72, 72, 72, 72, 81, 78, 78, 79),
    # Na 2023 niet meer in de Kerncijfers
    "Huishoudens met laag inkomen": _reeks("HuishoudensMetEenLaagInkomen", 78, 78, 78, 78, 87, None, None, None),
    # Vanaf 2023 heet het onderwijsniveau anders (basis/vmbo/mbo1, havo/vwo/mbo2-4, hbo/wo): zelfde indeling
    "Opleidingsniveau laag": {
        **_reeks("OpleidingsniveauLaag", 64, 64, 64, 64, None, None, None, None),
        **_reeks("BasisonderwijsVmboMbo1", None, None, None, None, 70, 67, 67, 68),
    },
    "Opleidingsniveau middelbaar": {
        **_reeks("OpleidingsniveauMiddelbaar", 65, 65, 65, 65, None, None, None, None),
        **_reeks("HavoVwoMbo24", None, None, None, None, 71, 68, 68, 69),
    },
    "Opleidingsniveau hoog": {
        **_reeks("OpleidingsniveauHoog", 66, 66, 66, 66, None, None, None, None),
        **_reeks("HboWo", None, None, None, None, 72, 69, 69, 70),
    },
    "Participatiewet totaal": _reeks("PersonenPerSoortUitkeringBijstand", 83, 83, 83, 83, 92, 87, 87, 88),
    "Personenauto's per huishouden": {
        **_reeks("PersonenautoSPerHuishouden", 102, 103, 103, 103, 112, None, None, None),
        **_reeks("PersonenautoSParticulierenPerHh", None, None, None, None, None, 107, 107, 108),
    },
    "Personenauto's naar oppervlakte": {
        **_reeks("PersonenautoSNaarOppervlakte", 103, 104, 104, 104, 113, None, None, None),
        **_reeks("PersonenautoSParticulierenOppervlakte", None, None, None, None, None, 108, 108, 109),
    },
    "Afstand tot huisarts": _reeks("AfstandTotHuisartsenpraktijk", 105, 106, 106, 106, 115, 110, 110, 111),
    "Afstand tot grote supermarkt": _reeks("AfstandTotGroteSupermarkt", 106, 107, 107, 107, 116, 111, 111, 112),
    "Afstand tot kinderdagverblijf": _reeks("AfstandTotKinderdagverblijf", 107, 108, 108, 108, 117, 112, 112, 113),
    "Afstand tot school": _reeks("AfstandTotSchool", 108, 109, 109, 109, 118, 113, 113, 114),
}

# Jaren waarin CBS een variabele niet (meer) publiceert; de unittest eist dat MAPPING + dit = alle jaren.
NIET_GEPUBLICEERD = {
    "Huishoudens met laag inkomen": {2024, 2025, 2026},  # vervallen in de Kerncijfers na 2023
    "80 jaar of ouder": {2019, 2020, 2021, 2022, 2023, 2024, 2025},  # pas vanaf 2026 apart (daarvoor 65+)
}

VELDEN = [
    "gebied_id",
    "indicator_uuid",
    "indicator_naam",
    "waarde",
    "jaar",
    "bron",
    "kwaliteit",
    "eenheid",
    "categorie",
    "interpretatie_logica",
    "scenario_id",
    "bron_tabel",
]


def bron_naam(jaar):
    return f"CBS Kerncijfers wijken en buurten {jaar} ({TABELLEN[jaar]})"


def kolommen(jaar):
    """Alle CBS-kolommen die voor dit jaar nodig zijn."""
    uit = []
    for per_jaar in MAPPING.values():
        k = per_jaar.get(jaar)
        if k:
            uit.extend(k if isinstance(k, tuple) else [k])
    return sorted(set(uit))


def geometrie_codes():
    geo = json.loads(GEOMETRIE.read_text(encoding="utf-8"))
    return {f["properties"]["buurtcode"]: f["properties"]["gemeentenaam"] for f in geo["features"]}


def _get(session, url, params=None):
    for poging in range(4):
        try:
            r = session.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception:
            if poging == 3:
                raise
            time.sleep(2 * (poging + 1))


def controleer_tabel(session, jaar, tabel, log=print):
    """TableInfos.Period moet het peiljaar zijn; alle kolommen uit de mapping moeten bestaan."""
    info = _get(session, f"{CBS_API}/{tabel}/TableInfos", {"$format": "json"})["value"][0]
    periode = str(info.get("Period", "")).strip()
    if periode != str(jaar):
        raise RuntimeError(f"❌ {tabel}: Period is '{periode}', verwacht {jaar} ({info.get('Title')})")
    props = _get(session, f"{CBS_API}/{tabel}/DataProperties", {"$format": "json"})["value"]
    sleutels = {p["Key"] for p in props}
    ontbreekt = [k for k in kolommen(jaar) if k not in sleutels]
    if ontbreekt:
        raise RuntimeError(f"❌ {tabel} ({jaar}): kolommen ontbreken: {ontbreekt}")
    log(f"   ✅ {tabel}: {info.get('Title')} · Period {periode} · {len(kolommen(jaar))} kolommen")
    return info.get("Title")


def haal_buurten(session, tabel, cols, codes=None):
    """Buurten uit één tabel: alle Friese buurten, of alleen `codes`. Filter op de dimensie
    WijkenEnBuurten: een filter op Codering_3 negeert CBS stil (dan komt heel Nederland mee).
    ODataApi geeft max. 10.000 rijen, Fryslân heeft er ~1.000."""
    select = ",".join(["Codering_3"] + cols)
    if codes:
        rijen = []
        lijst = sorted(codes)
        for i in range(0, len(lijst), 40):  # URL-lengte beperken
            filt = " or ".join(f"WijkenEnBuurten eq '{c:<10}'" for c in lijst[i : i + 40])
            params = {"$format": "json", "$filter": filt, "$select": select}
            rijen += _get(session, f"{CBS_API}/{tabel}/TypedDataSet", params)["value"]
        return rijen
    filt = " or ".join(f"startswith(WijkenEnBuurten,'BU{gm}')" for gm in FRIESE_GM_CODES)
    params = {"$format": "json", "$filter": filt, "$select": select, "$top": 9999}
    rijen = _get(session, f"{CBS_API}/{tabel}/TypedDataSet", params)["value"]
    if len(rijen) >= 9999:
        sys.exit(f"❌ {tabel}: te veel rijen ({len(rijen)}); filter controleren")
    return rijen


def waarde_van(record, kolom):
    if isinstance(kolom, tuple):
        delen = [record.get(k) for k in kolom]
        if any(d is None for d in delen):
            return None
        return float(sum(delen))
    v = record.get(kolom)
    return None if v is None else float(v)


def rij(gebied, naam, waarde, jaar):
    ind_uuid, eenheid, logica, categorie = INDICATOREN[naam]
    w = round(waarde, 4)
    return {
        "gebied_id": gebied,
        "indicator_uuid": ind_uuid,
        "indicator_naam": naam,
        "waarde": int(w) if w == int(w) else w,
        "jaar": jaar,
        "bron": bron_naam(jaar),
        "kwaliteit": "",
        "eenheid": eenheid,
        "categorie": categorie,
        "interpretatie_logica": logica,
        "scenario_id": "current",
        "bron_tabel": TABELLEN[jaar],
    }


def weggevallen_boven_drempel(weg_waarden, opgenomen, max_fractie=MAX_WEGGEVALLEN):
    """Jaargangen waarin meer dan max_fractie van de waarden bij buurtcodes zonder geometrie hoort.
    weg_waarden en opgenomen: {jaar: aantal}. Geeft [(jaar, weg, totaal)] terug."""
    uit = []
    for jaar in sorted(set(weg_waarden) | set(opgenomen)):
        weg, totaal = weg_waarden.get(jaar, 0), weg_waarden.get(jaar, 0) + opgenomen.get(jaar, 0)
        if totaal and weg / totaal > max_fractie:
            uit.append((jaar, weg, totaal))
    return uit


def download(codes=None, log=print):
    """Download de reeksen. codes=None: alle Friese buurten. Geeft (rijen, verslag) terug.
    Alleen buurtcodes uit de geometrie van GEOMETRIE_JAAR worden opgenomen."""
    import requests

    session = requests.Session()
    geo = geometrie_codes()
    titels, rijen, weg, ontbreekt_in_tabel, weg_waarden = {}, [], {}, {}, Counter()
    opgenomen = {}
    for jaar, tabel in TABELLEN.items():
        titels[jaar] = controleer_tabel(session, jaar, tabel, log)
        records = haal_buurten(session, tabel, kolommen(jaar), codes)
        tabelcodes = {r["Codering_3"].strip() for r in records}
        weg_jaar = defaultdict(list)
        n_voor = len(rijen)
        for rec in records:
            code = rec["Codering_3"].strip()
            if code not in geo:
                weg_jaar[f"GM{code[2:6]}"].append(code)
                weg_waarden[jaar] += sum(waarde_van(rec, k[jaar]) is not None for k in MAPPING.values() if k.get(jaar))
                continue
            per_ind = {}
            for naam, per_jaar in MAPPING.items():
                kol = per_jaar.get(jaar)
                if not kol:
                    continue
                w = waarde_van(rec, kol)
                if w is not None:
                    per_ind[naam] = w
                    rijen.append(rij(code, naam, w, jaar))
            for naam, a in AFGELEID.items():
                t, n = per_ind.get(a["teller"]), per_ind.get(a["noemer"])
                if t is not None and n:
                    rijen.append(rij(code, naam, round(t / n * a["factor"], 1), jaar))
        weg[jaar] = {gm: sorted(c) for gm, c in sorted(weg_jaar.items())}
        opgenomen[jaar] = len(rijen) - n_voor
        doel = set(codes) if codes else set(geo)
        ontbreekt_in_tabel[jaar] = len(doel - tabelcodes)
        log(f"   📥 {jaar}: {len(records)} buurten · {len(rijen) - n_voor} waarden")
        time.sleep(0.3)
    te_veel = weggevallen_boven_drempel(weg_waarden, opgenomen)
    if te_veel:
        sys.exit(
            "❌ Te veel waarden van buurtcodes zonder geometrie "
            + str(GEOMETRIE_JAAR)
            + " (max "
            + f"{MAX_WEGGEVALLEN:.0%}): "
            + ", ".join(f"{j}: {w} van {t} ({w / t:.1%})" for j, w, t in te_veel)
            + ". Nieuwe buurtindeling? Werk de geometrie bij, of verhoog MAX_WEGGEVALLEN bewust."
        )
    rijen.sort(key=lambda r: (r["gebied_id"], r["indicator_naam"], r["jaar"]))
    return rijen, {
        "titels": titels,
        "weg": weg,
        "ontbreekt_in_tabel": ontbreekt_in_tabel,
        "weg_waarden": weg_waarden,
        "geo": geo,
    }


def cache_pad(codes=None):
    """Fryslân-cache, of een cachebestand per set buurten."""
    if not codes:
        return CACHE_DIR / "kerncijfers_fryslan.csv"
    sleutel = hashlib.sha1(",".join(sorted(codes)).encode()).hexdigest()[:12]
    return CACHE_DIR / f"kerncijfers_{len(codes)}buurten_{sleutel}.csv"


def schrijf_csv(pad, rijen):
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=VELDEN, lineterminator="\n")
        w.writeheader()
        w.writerows(rijen)


def lees_csv(pad, codes=None):
    with open(pad, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if not codes or r["gebied_id"] in codes]


def rijen_voor(codes, log=print):
    """Reeksen voor deze buurten: uit de cache (Fryslân-cache of eerdere download van dezelfde set),
    anders downloaden bij CBS en in de cache zetten. Downloadfouten gaan naar de aanroeper."""
    codes = sorted(set(codes))
    fryslan = cache_pad()
    if fryslan.exists():
        log(f"   💾 uit cache: {fryslan}")
        return lees_csv(fryslan, set(codes))
    pad = cache_pad(codes)
    if pad.exists():
        log(f"   💾 uit cache: {pad}")
        return lees_csv(pad)
    log(f"   🌐 downloaden bij CBS: {len(codes)} buurten, {len(TABELLEN)} jaargangen")
    rijen, _ = download(codes, log)
    try:
        schrijf_csv(pad, rijen)
    except OSError as e:  # cache niet schrijfbaar: wel laden, volgende keer opnieuw downloaden
        log(f"   ⚠️  cache niet schrijfbaar ({e}); data wordt wel geladen")
    return rijen


def schrijf_package(rijen, verslag):
    """Recept en codecontrole in git (geen data): init_data/cbs/datapackage.json."""
    geo, weg, titels = verslag["geo"], verslag["weg"], verslag["titels"]
    gm_naam = {f"GM{code[2:6]}": gnaam for code, gnaam in geo.items()}
    per_ind = defaultdict(set)
    for r in rijen:
        per_ind[r["indicator_naam"]].add(r["jaar"])
    package = {
        "name": "cbs-kerncijfers-fryslan",
        "title": "CBS Kerncijfers wijken en buurten 2019-%d, buurten in Fryslân" % max(TABELLEN),
        "description": "Recept voor de Kerncijfers wijken en buurten van alle jaargangen vanaf 2019 voor de "
        "buurten in Fryslân, gemapt op de indicatoren van D-OmniTwin. De data zelf staat niet in "
        "git: init_data/scripts/laad_cbs.py downloadt bij het laden van een use case, met cache "
        "in $DATA_CACHE. Jaar = peiljaar van de CBS-tabel. Alleen buurtcodes die in de "
        f"CBS-geometrie {GEOMETRIE_JAAR} bestaan.",
        "licenses": [
            {
                "name": "CC-BY-4.0",
                "title": "Creative Commons Attribution 4.0",
                "path": "https://creativecommons.org/licenses/by/4.0/",
            }
        ],
        "sources": [
            {"title": bron_naam(j), "path": f"https://opendata.cbs.nl/statline/#/CBS/nl/dataset/{t}"}
            for j, t in TABELLEN.items()
        ],
        "bronvermelding": "Centraal Bureau voor de Statistiek (CBS), Kerncijfers wijken en buurten 2019-%d. "
        "CC BY 4.0." % max(TABELLEN),
        "geometrie_jaar": GEOMETRIE_JAAR,
        "gecontroleerd": date.today().isoformat(),
        "tabellen": {str(j): {"tabel": t, "titel": titels[j], "peiljaar": j} for j, t in TABELLEN.items()},
        "indicatoren": {
            n: {
                "uuid": INDICATOREN[n][0],
                "jaren": sorted(per_ind[n]),
                "kolommen": {str(j): (list(k) if isinstance(k, tuple) else k) for j, k in MAPPING.get(n, {}).items()}
                if n in MAPPING
                else None,
                "afgeleid": AFGELEID.get(n),
            }
            for n in INDICATOREN
        },
        "controle": {
            "toelichting": "Omvang van een volledige download (heel Fryslân), om een nieuwe download mee te "
            "vergelijken.",
            "rijen_totaal": len(rijen),
            "rijen_per_jaar": {str(j): sum(1 for r in rijen if r["jaar"] == j) for j in TABELLEN},
        },
        "codecontrole": {
            "toelichting": f"Buurtcodes uit de CBS-tabel die niet in de geometrie {GEOMETRIE_JAAR} bestaan, "
            "per peiljaar en gemeente. Deze waarden worden niet opgenomen.",
            "weggevallen": {
                str(j): {f"{gm} {gm_naam.get(gm, '?')}": len(c) for gm, c in g.items()} for j, g in weg.items()
            },
            "weggevallen_waarden": {str(j): verslag["weg_waarden"][j] for j in TABELLEN},
            "weggevallen_codes": {str(j): g for j, g in weg.items() if g},
            "geometriebuurten_zonder_tabelrij": {str(j): n for j, n in verslag["ontbreekt_in_tabel"].items()},
        },
    }
    UIT_PACKAGE.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="CBS Kerncijfers wijken en buurten (alle jaargangen) voor Fryslân")
    parser.add_argument("codes", nargs="*", help="buurtcodes (BU...) om naar de cache te downloaden")
    parser.add_argument("--controle", action="store_true", help="alleen tabellen (Period) en kolommen controleren")
    parser.add_argument("--alle", action="store_true", help="heel Fryslân naar de cache, en datapackage.json bijwerken")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # emoji op Windows-consoles
    if args.controle:
        import requests

        session = requests.Session()
        for jaar, tabel in TABELLEN.items():
            controleer_tabel(session, jaar, tabel)
        print("✅ Alle tabellen en kolommen kloppen.")
        return
    if args.alle:
        rijen, verslag = download(None)
        schrijf_csv(cache_pad(), rijen)
        schrijf_package(rijen, verslag)
        print(f"✅ {len(rijen)} rijen → {cache_pad()} · recept bijgewerkt: {UIT_PACKAGE.relative_to(ROOT)}")
        return
    if not args.codes:
        parser.error("geef buurtcodes, of --alle, of --controle")
    rijen = rijen_voor(args.codes)
    print(f"✅ {len(rijen)} rijen voor {len(args.codes)} buurten")


if __name__ == "__main__":
    main()
