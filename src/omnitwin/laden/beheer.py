"""
Beheerroute in-process: inrichting uit een use case (Kompasprofielen, externe kaartlagen)
=========================================================================================
Een dataset met `route: beheer` levert geen waarden maar inrichting. Over HTTP hoort daar
`PUT /api/beheer/v1/<soort>/<id>` bij (nog niet gebouwd); bij de eerste installatie
(`installeer --inproces`, db-init) voert `omnitwin.laden.inproces.InprocesLaadApi.beheer` hem
hier uit, met de verbinding van de databasebeheerder (zelfde rechten als `load_sample.py`).

De levering is een Data Package-zip met één resource (Table Schema in de use case). Beleid,
gelijk aan de stuurdata (`import_kompasprofielen` in `init_data/scripts/load_sample.py`):
**aanvullen, nooit overschrijven.** Wat er al is (een koppeling, een laag met dezelfde naam)
blijft zoals het is; herhalen is idempotent.

| Soort (`beheerpad`) | Doel | Per regel |
|---|---|---|
| `kompasprofielen` | kompas_configuraties, kompas_titels, kompas_themas, kompas_onderdelen, kompas_indicator_mapping | profiel, kwadrant, thema, onderdeel, indicator_uuid, weging, is_actueel; een onbekende indicator wordt overgeslagen en geteld |
| `externe-kaartlagen` | externe_kaartlagen | de velden van het beheerscherm (ExterneKaartlaagCreate) plus `toegang`; `intern` wordt (tot de toegang per laag er is, #254) niet actief gezet |
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from contextlib import contextmanager
from pathlib import Path

WAAR = {"true", "t", "1", "ja", "j", "yes"}


def lees_resource(pad) -> list[dict]:
    """De (eerste) resource van een Data Package-zip als lijst records (strings; leeg = None)."""
    with zipfile.ZipFile(pad) as z:
        pakket = json.loads(z.read("datapackage.json"))
        resource = pakket["resources"][0]
        tekst = z.read(resource["path"]).decode("utf-8-sig")
    return [{k: (None if v == "" else v) for k, v in r.items()} for r in csv.DictReader(io.StringIO(tekst))]


def _bool(w, standaard=False) -> bool:
    return standaard if w is None else str(w).strip().lower() in WAAR


def _getal(w, standaard=None):
    return standaard if w is None else float(w)


def kompasprofielen(cur, regels: list[dict]) -> dict:
    """Kompasprofielen aanvullen: profiel aanmaken als hij niet bestaat, hiërarchie en koppelingen erbij."""
    uit = {"regels": len(regels), "nieuweProfielen": [], "gekoppeld": 0, "alAanwezig": 0, "indicatorOnbekend": []}
    profielen: dict[str, int] = {}
    for volgorde, r in enumerate(regels):
        naam = r["profiel"]
        if naam not in profielen:
            cur.execute("SELECT id FROM public.kompas_configuraties WHERE naam = %s", (naam,))
            rij = cur.fetchone()
            if rij is None:
                cur.execute("INSERT INTO public.kompas_configuraties (naam, is_standaard, is_actief) "
                            "VALUES (%s, false, true) RETURNING id", (naam,))
                rij = cur.fetchone()
                uit["nieuweProfielen"].append(naam)
            profielen[naam] = rij[0]
        config_id = profielen[naam]
        cur.execute("SELECT 1 FROM public.indicatoren WHERE uuid = %s", (r["indicator_uuid"],))
        if cur.fetchone() is None:
            uit["indicatorOnbekend"].append(r["indicator_uuid"])
            continue
        ouder = config_id
        for tabel, ouder_kolom, waarde in (("kompas_titels", "config_id", r["kwadrant"]),
                                           ("kompas_themas", "titel_id", r["thema"]),
                                           ("kompas_onderdelen", "thema_id", r.get("onderdeel") or "(Algemeen)")):
            cur.execute(f"SELECT id FROM public.{tabel} WHERE naam = %s AND {ouder_kolom} = %s", (waarde, ouder))
            rij = cur.fetchone()
            if rij is None:
                cur.execute(f"INSERT INTO public.{tabel} (naam, {ouder_kolom}, volgorde) VALUES (%s, %s, %s) RETURNING id",
                            (waarde, ouder, volgorde))
                rij = cur.fetchone()
            ouder = rij[0]
        cur.execute("""INSERT INTO public.kompas_indicator_mapping (config_id, indicator_uuid, onderdeel_id, weging, is_actueel)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (config_id, indicator_uuid, onderdeel_id) DO NOTHING""",
                    (config_id, r["indicator_uuid"], ouder, _getal(r.get("weging"), 1.0), _bool(r.get("is_actueel"), True)))
        uit["gekoppeld" if cur.rowcount else "alAanwezig"] += 1
    return uit


def externe_kaartlagen(cur, regels: list[dict]) -> dict:
    """Externe kaartlagen (WFS/WMS/GeoJSON) toevoegen; een laag met dezelfde naam blijft ongewijzigd."""
    from omnitwin.routers.externe_lagen import ExterneKaartlaagCreate
    uit = {"regels": len(regels), "toegevoegd": [], "alAanwezig": [], "internNietActief": []}
    for r in regels:
        toegang = (r.pop("toegang", None) or "openbaar").strip().lower()
        velden = {k: v for k, v in r.items() if v is not None}
        if "opacity" in velden:
            velden["opacity"] = float(velden["opacity"])
        if "volgorde" in velden:
            velden["volgorde"] = int(float(velden["volgorde"]))
        if "actief" in velden:
            velden["actief"] = _bool(velden["actief"])
        laag = ExterneKaartlaagCreate(**velden).model_dump()
        if toegang == "intern" and laag["actief"]:
            laag["actief"] = False  # tot de toegang per laag (#254): intern = niet openbaar zichtbaar
            uit["internNietActief"].append(laag["naam"])
        cur.execute("SELECT 1 FROM public.externe_kaartlagen WHERE naam = %s", (laag["naam"],))
        if cur.fetchone():
            uit["alAanwezig"].append(laag["naam"])
            continue
        kolommen = list(laag)
        cur.execute(f"INSERT INTO public.externe_kaartlagen ({', '.join(kolommen)}) "
                    f"VALUES ({', '.join(['%s'] * len(kolommen))})", [laag[k] for k in kolommen])
        uit["toegevoegd"].append(laag["naam"])
    return uit


SOORTEN = {"kompasprofielen": kompasprofielen, "externe-kaartlagen": externe_kaartlagen}


@contextmanager
def transactie():
    """Eén transactie met de verbinding van de backend (in-process: de databasebeheerder)."""
    from omnitwin.database import engine
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def voer_uit(pad_api: str, bestand, transactie_=None) -> dict:
    """`pad_api` = /api/beheer/v1/<soort>/<id>. Geeft een resultaat zoals de laad-API (http, status, aantallen)."""
    delen = [d for d in str(pad_api).split("/") if d]
    soort = delen[-2] if len(delen) >= 2 else ""
    if soort not in SOORTEN:
        return {"http": 501, "status": "overgeslagen", "melding": f"{pad_api}: beheer-API niet in-process"}
    regels = lees_resource(Path(bestand))
    with (transactie_ or transactie)() as cur:
        aantallen = SOORTEN[soort](cur, regels)
    return {"http": 200, "status": "verwerkt", "soort": soort, "aantallen": aantallen}
