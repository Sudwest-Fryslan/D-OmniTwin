#!/usr/bin/env python3
"""
Hittestress — brondata ophalen uit officiële open bronnen
==========================================================
Schrijft usecases/hittestress/data/waarden.csv (formaat als
init_data/sample/2_brondata/sample_indicatoren.csv) voor de gebieden in
usecase.json. De CSV staat in git, zodat laden offline werkt; dit script is
alleen nodig om de data te verversen of te controleren.

Bronnen (per indicator, zie BRONNEN hieronder):

1. 65+ jaar (%) en 80 jaar of ouder (%)
   CBS, Kerncijfers wijken en buurten 2026 (tabel 86358NED), peildatum 1-1-2026.
   https://opendata.cbs.nl/ODataApi/odata/86358NED
   Licentie: CC BY 4.0. Berekend als (65-80 + 80+) ÷ inwoners en 80+ ÷ inwoners.
   CBS publiceert geen 75+ per buurt; 80+ is de dichtstbijzijnde (en voor hitte
   de meest kwetsbare) leeftijdsgroep.

2. Boomkroonbedekking (%)
   RIVM, Atlas Natuurlijk Kapitaal, Bomenkaart 2022 (10 x 10 m, percentage
   bomen hoger dan 2,5 m per gridcel).
   WCS https://data.rivm.nl/geo/ank/wcs, coverage ank__rivm_20231221_bomenkaart_2022
   Download https://data.rivm.nl/data/ank/rivm_20231221_bomenkaart_2022.zip
   Licentie: Public Domain Mark 1.0. Buurtwaarde = gemiddelde over de cellen
   waarvan het middelpunt in de buurt ligt; cellen zonder bomen (nodata) tellen als 0%.

3. Stedelijk hitte-eiland effect (°C)
   RIVM, Atlas Natuurlijk Kapitaal, Stedelijk hitte-eiland effect (UHI) v2,
   versie 01-06-2022 (10 x 10 m): gemiddeld luchttemperatuurverschil stad-land.
   WCS https://data.rivm.nl/geo/ank/wcs, coverage ank__Stedelijk_hitte_eiland_effect_01062022_v2
   Download https://data.rivm.nl/data/ank/Stedelijk_hitte_eiland_effect_01062022_v2.zip
   Licentie: Public Domain Mark 1.0. Buurtwaarde = gemiddelde over de cellen.
   Dit vervangt de gevoelstemperatuur (Klimaateffectatlas): die is voor Fryslân
   niet als open download of WCS beschikbaar (alleen opvraagbaar via de atlas).

De buurtgrenzen komen uit init_data/sample/2_brondata/sample_buurten.geojson
(CBS Wijk- en buurtkaart, WGS84), omgezet naar RD New (EPSG:28992).

Vereist: numpy, Pillow, shapely, pyproj (staan in requirements.txt).

Gebruik:
    python usecases/hittestress/maak_data.py
"""

import csv
import io
import json
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import numpy as np
import shapely
from PIL import Image
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent.parent
GEOJSON = ROOT / "init_data" / "sample" / "2_brondata" / "sample_buurten.geojson"
UIT = HIER / "data" / "waarden.csv"
VELDEN = ["gebied_id", "indicator_uuid", "indicator_naam", "waarde", "jaar", "bron", "kwaliteit",
          "eenheid", "categorie", "interpretatie_logica", "scenario_id"]

# Zelfde namespace als init_data/scripts/laad_usecase.py: dezelfde naam geeft dezelfde uuid
NAMESPACE = uuid.UUID("6f1d3c2a-0b7e-4c8e-9a51-d0a1b2c3e4f5")

CBS_TABEL = "86358NED"
CBS_URL = f"https://opendata.cbs.nl/ODataApi/odata/{CBS_TABEL}"
RIVM_WCS = "https://data.rivm.nl/geo/ank/wcs"
NODATA = -9999

BRONNEN = {
    "65+ jaar (%)": {
        "bron": f"CBS Kerncijfers wijken en buurten 2026 ({CBS_TABEL}), CC BY 4.0",
        "jaar": 2026, "eenheid": "%", "categorie": "Bevolking", "logica": "pos_is_pos",
    },
    "80 jaar of ouder (%)": {
        "bron": f"CBS Kerncijfers wijken en buurten 2026 ({CBS_TABEL}), CC BY 4.0",
        "jaar": 2026, "eenheid": "%", "categorie": "Bevolking", "logica": "pos_is_pos",
    },
    "Boomkroonbedekking": {
        "bron": "RIVM Atlas Natuurlijk Kapitaal, Bomenkaart 2022 (10 m), Public Domain Mark 1.0",
        "jaar": 2022, "eenheid": "%", "categorie": "Klimaat", "logica": "pos_is_pos",
        "coverage": "ank__rivm_20231221_bomenkaart_2022", "nodata_is": 0.0, "decimalen": 1,
    },
    "Stedelijk hitte-eiland effect": {
        "bron": "RIVM Atlas Natuurlijk Kapitaal, Stedelijk hitte-eiland effect v2 (2022, 10 m), Public Domain Mark 1.0",
        "jaar": 2022, "eenheid": "°C", "categorie": "Klimaat", "logica": "-/+",  # lager is beter
        "coverage": "ank__Stedelijk_hitte_eiland_effect_01062022_v2", "nodata_is": None, "decimalen": 2,
    },
}


def haal(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "D-OmniTwin"}), timeout=120) as r:
        return r.read()


def gebieden():
    uc = json.loads((HIER / "usecase.json").read_text(encoding="utf-8"))
    return list(uc["data"]["gebieden"])


def cbs_leeftijd(ids):
    filt = " or ".join(f"WijkenEnBuurten eq '{i}'" for i in ids)
    velden = "WijkenEnBuurten,AantalInwoners_5,k_65JaarTot80Jaar_12,k_80JaarOfOuder_13"
    url = f"{CBS_URL}/TypedDataSet?" + urllib.parse.urlencode({"$filter": filt, "$select": velden})
    uit = {}
    for r in json.loads(haal(url))["value"]:
        gid, inw = r["WijkenEnBuurten"].strip(), r["AantalInwoners_5"]
        uit[gid] = {
            "65+ jaar (%)": round((r["k_65JaarTot80Jaar_12"] + r["k_80JaarOfOuder_13"]) / inw * 100, 1),
            "80 jaar of ouder (%)": round(r["k_80JaarOfOuder_13"] / inw * 100, 1),
        }
    return uit


def buurten_rd(ids):
    naar_rd = Transformer.from_crs(4326, 28992, always_xy=True).transform
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return {f["properties"]["id"]: transform(naar_rd, shape(f["geometry"]))
            for f in geo["features"] if f["properties"]["id"] in ids}


def wcs_raster(coverage, x0, y0, x1, y1):
    """GeoTIFF-uitsnede in RD; geeft (array, (originx, celx, originy, cely))."""
    url = f"{RIVM_WCS}?" + urllib.parse.urlencode([
        ("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"), ("CoverageId", coverage),
        ("format", "image/tiff"), ("subset", f"X({x0},{x1})"), ("subset", f"Y({y0},{y1})"),
    ])
    im = Image.open(io.BytesIO(haal(url)))
    m = im.tag_v2[34264]  # ModelTransformationTag: x = m0*col + m3, y = m5*row + m7
    return np.array(im, dtype="float64"), (m[3], m[0], m[7], m[5])


def raster_gemiddelde(polys, cfg):
    x0, y0, x1, y1 = shapely.union_all(list(polys.values())).bounds
    x0, y0 = np.floor(x0 / 10) * 10 - 20, np.floor(y0 / 10) * 10 - 20
    x1, y1 = np.ceil(x1 / 10) * 10 + 20, np.ceil(y1 / 10) * 10 + 20
    a, (ox, cx, oy, cy) = wcs_raster(cfg["coverage"], int(x0), int(y0), int(x1), int(y1))
    rij, kol = np.indices(a.shape)
    xs, ys = ox + (kol + 0.5) * cx, oy + (rij + 0.5) * cy  # celmiddelpunten
    nodata = a <= NODATA
    if cfg["nodata_is"] is not None:
        a = np.where(nodata, cfg["nodata_is"], a)
        nodata = np.zeros_like(nodata)
    uit = {}
    for gid, poly in polys.items():
        binnen = shapely.contains_xy(poly, xs, ys) & ~nodata
        uit[gid] = round(float(a[binnen].mean()), cfg["decimalen"])
        print(f"   {gid}: {binnen.sum()} cellen, gemiddeld {uit[gid]}")
    return uit


def main():
    ids = gebieden()
    print(f"Gebieden: {ids}")
    waarden = {gid: {} for gid in ids}

    print(f"CBS {CBS_TABEL}: leeftijd")
    for gid, w in cbs_leeftijd(ids).items():
        waarden[gid].update(w)

    polys = buurten_rd(ids)
    for naam, cfg in BRONNEN.items():
        if "coverage" in cfg:
            print(f"RIVM WCS {cfg['coverage']}: {naam}")
            for gid, w in raster_gemiddelde(polys, cfg).items():
                waarden[gid][naam] = w

    UIT.parent.mkdir(exist_ok=True)
    with open(UIT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=VELDEN, lineterminator="\n")
        w.writeheader()
        for gid in ids:
            for naam, cfg in BRONNEN.items():
                if naam not in waarden[gid]:
                    raise SystemExit(f"Geen waarde voor {naam} / {gid}")
                w.writerow({
                    "gebied_id": gid, "indicator_uuid": str(uuid.uuid5(NAMESPACE, naam)), "indicator_naam": naam,
                    "waarde": waarden[gid][naam], "jaar": cfg["jaar"], "bron": cfg["bron"], "kwaliteit": "",
                    "eenheid": cfg["eenheid"], "categorie": cfg["categorie"],
                    "interpretatie_logica": cfg["logica"], "scenario_id": "current",
                })
    print(f"Geschreven: {UIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
