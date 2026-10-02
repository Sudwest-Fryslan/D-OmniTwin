"""
Profiel waarnemingen → gebied_data
==================================
Contract: `docs/api/laden/profielen/waarnemingen.schema.json`.

Controle in Python (per regel): Table Schema, precies één van jaar en peildatum, n-drempel
(`minimumN`, `minimumNPerIndicator`, `bijNOnderDrempel`, `bijOntbrekendeN`), dubbele sleutel.
Controle in SQL (na staging): gebied bestaat (en is van het opgegeven gebiedstype),
gebiedstype bestaat, indicator bestaat en is, als hij relaties heeft, gekoppeld aan het
gebiedstype van het gebied, waarde binnen min_waarde/max_waarde.

Een indicator zonder relaties in `indicator_gebiedstype_relaties` mag op elk gebiedstype
(de CBS-indicatoren hebben geen relaties; aanname, gedocumenteerd in docs/api/laden/README.md).

Publicatie (één transactie): de vorige inhoud van de dataset binnen het vervangbereik gaat uit
`laden.waarnemingen`, de nieuwe regels (zonder de onderdrukte) gaan erin, en voor alle geraakte
sleutels wordt `gebied_data` opnieuw opgebouwd uit `laden.waarnemingen`: per sleutel de waarde
van de dataset met voorrang (`LADEN_VOORRANG`, aanname A6 van #222), anders de laatst gepubliceerde.
"""

from __future__ import annotations

from omnitwin.laden import adapter_swf
from omnitwin.laden.basis import Afkeuring, Context, Fouten, afkeuren, copy, sql_fouten
from omnitwin.laden.lezen import Bron
from omnitwin.laden.problemen import Fout
from omnitwin.laden.tabelschema import Tabel, laad_schema

PROFIEL = "waarnemingen"
RESOURCE = "waarnemingen"
STAGING_KOLOMMEN = ["levering_id", "regel", "gebied_code", "gebiedstype", "indicator_uuid", "jaar", "datum",
                    "scenario_id", "waarde", "n", "n_status", "kwaliteit", "bron", "opmerking", "metadata"]
BEREIK_KOLOM = {"indicator_uuid": "indicator_uuid", "gebiedstype": "gebiedstype_id", "gebied_code": "gebied_id",
                "jaar": "jaar", "scenario": "scenario_id"}


def schema_en_extra(lp: dict) -> tuple[dict, dict]:
    """Het profielschema, en de extra velden uit een eigen schema in het laadprofiel (naar metadata)."""
    schema = laad_schema("waarnemingen")
    eigen = lp.get("schema") or {}
    profielvelden = {f["name"] for f in schema["fields"]}
    extra = {f["name"]: f for f in eigen.get("fields", []) if f.get("name") not in profielvelden}
    return schema, extra


def controleer(bron: Bron, ctx: Context, prefixen: dict[str, str]) -> tuple[list[tuple], Fouten, dict]:
    """(stagingregels, fouten, aantallen) van een levering."""
    lp = ctx.laadprofiel
    fouten, aantallen = Fouten(), {}
    schema, extra = schema_en_extra(lp)
    tabel = Tabel(schema, RESOURCE, extra)
    resource = RESOURCE
    if lp.get("adapter") == adapter_swf.ADAPTER and adapter_swf.is_waarden(bron.json):
        regels, adapterfouten, eind = adapter_swf.waarden_naar_waarnemingen(bron.json, prefixen)
        fouten.voeg_alle(adapterfouten)
        resource = "waarden"
        tabel.resource = resource
        if eind:
            aantallen["eindgeldigheidGenegeerd"] = eind
        strikt = False
    elif RESOURCE in bron.resources:
        res = bron.resources[RESOURCE]
        regels = res.regels
        strikt = res.kop is not None
        if res.kop is not None:
            fouten.voeg_alle(tabel.controleer_kop(res.kop))
    elif bron.json is not None and len(bron.resources) == 1:
        regels, strikt = next(iter(bron.resources.values())).regels, False
    else:
        raise afkeuren("formaat-ongeldig", f"resource {RESOURCE} ontbreekt (gevonden: "
                       f"{', '.join(sorted(bron.resources)) or 'geen'})")
    if fouten and any(f.regel is None for f in fouten.lijst):
        raise Afkeuring(fouten, {"gelezen": len(regels)})
    ctx.extra["resource"] = resource

    minimum_n = lp.get("minimumN", 10)
    per_indicator = {k.lower(): v for k, v in (lp.get("minimumNPerIndicator") or {}).items()}
    onder_drempel = lp.get("bijNOnderDrempel", "onderdrukken")
    ontbrekend = lp.get("bijOntbrekendeN", "afkeuren")
    sleutelvelden = lp.get("sleutelvelden") or ["gebied_code", "indicator_uuid", "jaar", "peildatum", "scenario"]
    al_fout = set(fouten.regels)  # adapterfouten (bijv. jaar-ongeldig) niet dubbel melden
    gezien: dict[tuple, int] = {}
    staging, onderdrukt, bron_onderdrukt = [], 0, 0
    lid = ctx.levering_id
    for i, ruw in enumerate(regels, start=1):
        r, rfouten = tabel.rij(ruw, i)
        for f in rfouten:
            fouten.voeg(f)
        if (r.get("jaar") is None) == (r.get("peildatum") is None) and (resource, i) not in al_fout:
            fouten.voeg(Fout("jaar-ongeldig", "precies één van jaar en peildatum moet gevuld zijn", resource, i, "jaar"))
        scenario = r.get("scenario") or "current"
        n = r.get("n")
        if n is None:
            if ontbrekend == "afkeuren":
                fouten.voeg(Fout("n-ontbreekt", "n is leeg; de dataset staat dat niet toe (bijOntbrekendeN)",
                                 resource, i, "n"))
            n_status = "bron-onderdrukt"
        else:
            drempel = per_indicator.get(str(r.get("indicator_uuid") or ""), minimum_n)
            if n < drempel:
                if onder_drempel == "afkeuren":
                    fouten.voeg(Fout("n-onder-drempel", f"n is kleiner dan de drempel {drempel}", resource, i, "n"))
                n_status = "onderdrukt"
            else:
                n_status = "gemeten"
        sleutel = tuple(scenario if v == "scenario" else r.get(v) for v in sleutelvelden)
        eerder = gezien.setdefault(sleutel, i)
        if eerder != i:
            fouten.voeg(Fout("dubbele-sleutel", f"regel {i} heeft dezelfde sleutel als regel {eerder}", resource, i))
        if (resource, i) in fouten.regels:
            continue
        if n_status == "onderdrukt":
            onderdrukt += 1
        elif n_status == "bron-onderdrukt":
            bron_onderdrukt += 1
        staging.append((lid, i, r["gebied_code"], r.get("gebiedstype"), r["indicator_uuid"], r.get("jaar"),
                        r.get("peildatum"), scenario, r["waarde"], n, n_status, r.get("kwaliteit"), r.get("bron"),
                        r.get("opmerking"), r.get("_metadata")))
    aantallen.update(gelezen=len(regels), fout=fouten.foute_regels, geldig=len(regels) - fouten.foute_regels,
                     onderdrukt=onderdrukt, bronOnderdrukt=bron_onderdrukt)
    return staging, fouten, aantallen


def prefixen(cur) -> dict[str, str]:
    """gebiedstype-id → code_prefix (gebiedstypes.metadata, profiel definities)."""
    cur.execute("SELECT id::text AS id, metadata->>'code_prefix' AS p FROM public.gebiedstypes "
                "WHERE coalesce(metadata->>'code_prefix', '') <> ''")
    return {r["id"]: r["p"] for r in cur.fetchall()}


def stage(cur, staging: list[tuple]) -> None:
    copy(cur, "laden.staging_waarnemingen", STAGING_KOLOMMEN, staging)


DB_CONTROLES = [
    ("gebiedstype-onbekend", "gebiedstype",
     """SELECT s.regel FROM laden.staging_waarnemingen s
        WHERE s.levering_id = %(lv)s AND s.gebiedstype IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.gebiedstypes t
                          WHERE t.id::text = lower(s.gebiedstype) OR t.code = s.gebiedstype)
        ORDER BY s.regel LIMIT 1000""",
     "gebiedstype bestaat niet"),
    ("gebied-onbekend", "gebied_code",
     """SELECT s.regel FROM laden.staging_waarnemingen s
        WHERE s.levering_id = %(lv)s
          AND NOT EXISTS (SELECT 1 FROM public.gebieden g WHERE g.id = s.gebied_code)
        ORDER BY s.regel LIMIT 1000""",
     "gebied_code komt niet voor in D-OmniTwin"),
    ("gebied-onbekend", "gebied_code",
     """SELECT s.regel, t.code AS gt FROM laden.staging_waarnemingen s
        JOIN public.gebieden g ON g.id = s.gebied_code
        JOIN public.gebiedstypes t ON t.id::text = lower(s.gebiedstype) OR t.code = s.gebiedstype
        WHERE s.levering_id = %(lv)s AND g.gebiedstype_id <> t.id
        ORDER BY s.regel LIMIT 1000""",
     "gebied_code komt niet voor in gebiedstype {gt}"),
    ("indicator-onbekend", "indicator_uuid",
     """SELECT s.regel FROM laden.staging_waarnemingen s
        WHERE s.levering_id = %(lv)s
          AND NOT EXISTS (SELECT 1 FROM public.indicatoren i WHERE i.uuid = s.indicator_uuid)
        ORDER BY s.regel LIMIT 1000""",
     "indicator bestaat niet"),
    ("indicator-onbekend", "indicator_uuid",
     """SELECT s.regel FROM laden.staging_waarnemingen s
        JOIN public.gebieden g ON g.id = s.gebied_code
        WHERE s.levering_id = %(lv)s
          AND EXISTS (SELECT 1 FROM public.indicator_gebiedstype_relaties r WHERE r.indicator_uuid = s.indicator_uuid)
          AND NOT EXISTS (SELECT 1 FROM public.indicator_gebiedstype_relaties r
                          WHERE r.indicator_uuid = s.indicator_uuid AND r.gebiedstype_id = g.gebiedstype_id)
        ORDER BY s.regel LIMIT 1000""",
     "indicator is niet gekoppeld aan het gebiedstype van het gebied"),
    ("waarde-buiten-bereik", "waarde",
     """SELECT s.regel FROM laden.staging_waarnemingen s
        JOIN public.indicatoren i ON i.uuid = s.indicator_uuid
        WHERE s.levering_id = %(lv)s
          AND ((i.min_waarde IS NOT NULL AND s.waarde < i.min_waarde)
            OR (i.max_waarde IS NOT NULL AND s.waarde > i.max_waarde))
        ORDER BY s.regel LIMIT 1000""",
     "waarde buiten min_waarde/max_waarde van de indicator"),
]


def db_controles(cur, ctx: Context, fouten: Fouten) -> None:
    resource = ctx.extra.get("resource", RESOURCE)
    for code, veld, sql, melding in DB_CONTROLES:
        sql_fouten(cur, fouten, sql, {"lv": ctx.levering_id}, code, resource, veld, melding)
    # Gebiedstype van het gebied vastleggen (vervangbereik, voorrang)
    cur.execute("""UPDATE laden.staging_waarnemingen s SET gebiedstype_id = g.gebiedstype_id
                   FROM public.gebieden g WHERE s.levering_id = %(lv)s AND g.id = s.gebied_code""",
                {"lv": ctx.levering_id})


def _bereik_voorwaarde(lp: dict) -> str:
    velden = lp.get("vervangBereik") or []
    onbekend = [v for v in velden if v not in BEREIK_KOLOM]
    if onbekend:
        raise afkeuren("schema-ongeldig", f"vervangBereik bevat onbekende velden: {', '.join(onbekend)}")
    if not velden:
        return ""
    kol = [BEREIK_KOLOM[v] for v in velden]
    return (f" AND ({', '.join('w.' + k for k in kol)}) IN (SELECT DISTINCT {', '.join('s.' + k for k in kol)} "
            f"FROM laden.staging_waarnemingen s WHERE s.levering_id = %(lv)s)")


SLEUTEL_GELIJK = """{a}.gebied_id = {b}.gebied_id AND {a}.indicator_uuid = {b}.indicator_uuid
    AND {a}.jaar IS NOT DISTINCT FROM {b}.jaar AND {a}.datum IS NOT DISTINCT FROM {b}.datum
    AND coalesce({a}.scenario_id, 'current') = {b}.scenario_id"""


def publiceer(cur, ctx: Context) -> dict:
    """Vervang de inhoud binnen het vervangbereik en bouw gebied_data op voor de geraakte sleutels."""
    lp, p = ctx.laadprofiel, {"lv": ctx.levering_id, "ds": ctx.dataset_id, "voorrang": list(ctx.voorrang)}
    cur.execute("""CREATE TEMP TABLE _weg (gebied_id varchar(100), indicator_uuid uuid, jaar integer,
                   datum timestamp, scenario_id varchar(50)) ON COMMIT DROP""")
    cur.execute(f"""WITH d AS (DELETE FROM laden.waarnemingen w WHERE w.dataset_id = %(ds)s{_bereik_voorwaarde(lp)}
                    RETURNING w.gebied_id, w.indicator_uuid, w.jaar, w.datum, w.scenario_id)
                    INSERT INTO _weg SELECT * FROM d""", p)
    vervangen = cur.rowcount
    cur.execute("""INSERT INTO laden.waarnemingen (dataset_id, levering_id, gebied_id, gebiedstype_id, indicator_uuid,
                       jaar, datum, scenario_id, waarde, n, n_status, kwaliteit, bron, opmerking, metadata)
                   SELECT %(ds)s, s.levering_id, s.gebied_code, s.gebiedstype_id, s.indicator_uuid, s.jaar, s.datum,
                          s.scenario_id, s.waarde, s.n, s.n_status, s.kwaliteit, s.bron, s.opmerking, s.metadata
                   FROM laden.staging_waarnemingen s
                   WHERE s.levering_id = %(lv)s AND s.n_status <> 'onderdrukt'""", p)
    gepubliceerd = cur.rowcount
    plausibel(lp, gepubliceerd, vervangen)

    # Geraakte sleutels: wat wegging en wat erbij kwam
    cur.execute("""CREATE TEMP TABLE _sleutels ON COMMIT DROP AS
                   SELECT DISTINCT gebied_id, indicator_uuid, jaar, datum, scenario_id FROM (
                       SELECT gebied_id, indicator_uuid, jaar, datum, scenario_id FROM _weg
                       UNION ALL
                       SELECT gebied_id, indicator_uuid, jaar, datum, scenario_id
                       FROM laden.waarnemingen WHERE levering_id = %(lv)s) x""", p)
    cur.execute("CREATE INDEX ON _sleutels (gebied_id, indicator_uuid)")
    cur.execute("ANALYZE _sleutels")
    cur.execute(f"DELETE FROM public.gebied_data g USING _sleutels k WHERE {SLEUTEL_GELIJK.format(a='g', b='k')}")
    cur.execute(f"""INSERT INTO public.gebied_data (gebied_id, indicator_uuid, waarde, jaar, datum, scenario_id, bron,
                        kwaliteit, metadata, n, n_status, levering_id)
                    SELECT DISTINCT ON (w.gebied_id, w.indicator_uuid, w.jaar, w.datum, w.scenario_id)
                           w.gebied_id, w.indicator_uuid, w.waarde, w.jaar, w.datum, w.scenario_id,
                           coalesce(w.bron, left(d.beschrijving->>'dct:title', 255)), w.kwaliteit,
                           jsonb_build_object('dataset', w.dataset_id) || coalesce(w.metadata, '{{}}'::jsonb),
                           w.n, w.n_status, w.levering_id
                    FROM laden.waarnemingen w
                    JOIN _sleutels k ON {SLEUTEL_GELIJK.format(a='w', b='k')}
                    JOIN laden.datasets d ON d.id = w.dataset_id
                    ORDER BY w.gebied_id, w.indicator_uuid, w.jaar, w.datum, w.scenario_id,
                             coalesce(array_position(%(voorrang)s::text[], w.dataset_id), 2147483647),
                             w.gepubliceerd_op DESC
                    ON CONFLICT DO NOTHING""", p)
    cur.execute("SELECT count(*) AS n FROM public.gebied_data WHERE levering_id = %(lv)s", p)
    zichtbaar = cur.fetchone()["n"]
    cur.execute("DELETE FROM laden.staging_waarnemingen WHERE levering_id = %(lv)s", p)
    cur.execute("SELECT count(*) AS n, array_agg(DISTINCT levering_id) AS ids FROM laden.waarnemingen "
                "WHERE dataset_id = %(ds)s", p)
    r = cur.fetchone()
    uit = {"gepubliceerd": gepubliceerd, "vervangen": vervangen, "_aantal_regels": r["n"],
           "_levering_ids": [str(x) for x in (r["ids"] or [])]}
    if zichtbaar < gepubliceerd:
        uit["nietZichtbaarDoorVoorrang"] = gepubliceerd - zichtbaar
    return uit


def plausibel(lp: dict, nieuw: int, vorig: int) -> None:
    """plausibiliteit uit het laadprofiel: minRegels en maxDalingProcent t.o.v. wat vervangen wordt."""
    pl = lp.get("plausibiliteit") or {}
    if pl.get("minRegels") is not None and nieuw < pl["minRegels"]:
        raise afkeuren("aantal-niet-plausibel", f"{nieuw} regels, minimaal {pl['minRegels']} (plausibiliteit.minRegels)")
    pct = pl.get("maxDalingProcent")
    if pct is not None and vorig and nieuw < vorig * (100 - pct) / 100:
        raise afkeuren("aantal-niet-plausibel", f"{nieuw} regels, de vorige versie had er binnen het vervangbereik "
                       f"{vorig}: meer dan {pct}% minder (plausibiliteit.maxDalingProcent)")
