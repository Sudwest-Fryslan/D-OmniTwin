"""
Profiel definities → indicatoren, gebiedstypes, indicator_gebiedstype_relaties
==============================================================================
Contract: `docs/api/laden/profielen/definities-*.schema.json`; adapter swf-monitor-v1:
`docs/api/laden/profielen/swf-monitor-v1.md`. Een levering is altijd de volledige set.

- indicatoren: upsert op uuid. Een leeg veld laat de bestaande waarde staan (behalve
  eindgeldigheid: die volgt de bron). Een indicator die deze dataset eerder leverde en nu
  ontbreekt, krijgt eindgeldigheid = moment van publicatie (niet verwijderd: waarden blijven
  herleidbaar). Status alleen een bekende code (STATUSSEN); een onbekende code is schema-ongeldig.
- gebiedstypen: upsert op id; code_prefix en gebiedsindeling_dataset (en bij de adapter wfs,
  typenames, sleutel, label) gaan naar gebiedstypes.metadata. Ontbreekt een eerder geleverd
  gebiedstype, dan wordt het inactief.
- relaties: volledige set; een eerder geleverde relatie die ontbreekt vervalt, tenzij er nog
  waarden aan hangen (fout relatie-in-gebruik).
"""

from __future__ import annotations

from omnitwin.laden import adapter_swf
from omnitwin.laden.basis import Afkeuring, Context, Fouten, afkeuren, copy, sql_fouten
from omnitwin.laden.lezen import Bron
from omnitwin.laden.p_waarnemingen import plausibel
from omnitwin.laden.problemen import Fout
from omnitwin.laden.tabelschema import Tabel, laad_schema

PROFIEL = "definities"
RESOURCES = {"indicatoren": "definities-indicatoren", "gebiedstypen": "definities-gebiedstypen",
             "relaties": "definities-relaties"}
STATUSSEN = ("C", "O", "B")  # indicatoren.status: Concept, Operationeel, Beëindigd


def controleer(bron: Bron, ctx: Context) -> tuple[dict, Fouten, dict]:
    lp = ctx.laadprofiel
    fouten = Fouten()
    if lp.get("adapter") == adapter_swf.ADAPTER and adapter_swf.is_definities(bron.json):
        bronregels = adapter_swf.definities_naar_resources(bron.json)
        koppen = {k: None for k in bronregels}
    else:
        ontbreekt = [r for r in RESOURCES if r not in bron.resources]
        if ontbreekt:
            raise afkeuren("formaat-ongeldig", f"resource(s) {', '.join(ontbreekt)} ontbreken; profiel definities "
                           "vraagt indicatoren, gebiedstypen en relaties")
        bronregels = {k: bron.resources[k].regels for k in RESOURCES}
        koppen = {k: bron.resources[k].kop for k in RESOURCES}
    uit, aantallen = {}, {"gelezen": 0, "perResource": {}}
    for naam, schema_naam in RESOURCES.items():
        tabel = Tabel(laad_schema(schema_naam), naam)
        if koppen[naam] is not None:
            fouten.voeg_alle(tabel.controleer_kop(koppen[naam]))
        rijen = []
        for i, ruw in enumerate(bronregels[naam], start=1):
            r, rf = tabel.rij(ruw, i)
            fouten.voeg_alle(rf)
            r["_regel"] = i
            r["_meta"] = ruw.get("_metadata") if isinstance(ruw.get("_metadata"), dict) else None
            rijen.append(r)
        uit[naam] = rijen
        aantallen["gelezen"] += len(rijen)
        aantallen["perResource"][naam] = len(rijen)
    if any(f.regel is None for f in fouten.lijst):
        raise Afkeuring(fouten, aantallen)

    for r in uit["indicatoren"]:
        if r.get("status") is not None and r["status"] not in STATUSSEN:
            fouten.voeg(Fout("schema-ongeldig", f"status is geen bekende code ({', '.join(STATUSSEN)})",
                             "indicatoren", r["_regel"], "status"))
    # Relaties verwijzen naar indicatoren en gebiedstypen in dezelfde levering (foreignKeys in het profiel)
    ind = {r["uuid"] for r in uit["indicatoren"] if r.get("uuid")}
    gts = {r["id"] for r in uit["gebiedstypen"] if r.get("id")}
    gezien = {}
    for r in uit["relaties"]:
        if r.get("indicator_uuid") and r["indicator_uuid"] not in ind:
            fouten.voeg(Fout("indicator-onbekend", "indicator_uuid staat niet in resource indicatoren",
                             "relaties", r["_regel"], "indicator_uuid"))
        if r.get("gebiedstype_id") and r["gebiedstype_id"] not in gts:
            fouten.voeg(Fout("gebiedstype-onbekend", "gebiedstype_id staat niet in resource gebiedstypen",
                             "relaties", r["_regel"], "gebiedstype_id"))
        sleutel = (r.get("indicator_uuid"), r.get("gebiedstype_id"))
        eerder = gezien.setdefault(sleutel, r["_regel"])
        if eerder != r["_regel"]:
            fouten.voeg(Fout("dubbele-sleutel", f"regel {r['_regel']} heeft dezelfde sleutel als regel {eerder}",
                             "relaties", r["_regel"]))
    aantallen.update(fout=fouten.foute_regels, geldig=aantallen["gelezen"] - fouten.foute_regels)
    return uit, fouten, aantallen


def stage(cur, ctx: Context, uit: dict) -> None:
    lid = ctx.levering_id
    copy(cur, "laden.staging_indicatoren",
         ["levering_id", "regel", "uuid", "naam", "code", "omschrijving", "eenheid", "score_type", "min_waarde",
          "max_waarde", "status", "begingeldigheid", "eindgeldigheid", "bron"],
         [(lid, r["_regel"], r["uuid"], r["naam"], r.get("code"), r.get("omschrijving"), r.get("eenheid"),
           r.get("score_type"), r.get("min_waarde"), r.get("max_waarde"), r.get("status"), r.get("begingeldigheid"),
           r.get("eindgeldigheid"), r.get("bron")) for r in uit["indicatoren"] if r.get("uuid") and r.get("naam")])
    gts = []
    for r in uit["gebiedstypen"]:
        if not (r.get("id") and r.get("naam")):
            continue
        meta = dict(r.get("_meta") or {})
        for k in ("gebiedsindeling_dataset", "code_prefix"):
            if r.get(k) is not None:
                meta[k] = r[k]
        gts.append((lid, r["_regel"], r["id"], r["naam"], r.get("code"), r.get("niveau"), r.get("actief"), meta or None))
    copy(cur, "laden.staging_gebiedstypen", ["levering_id", "regel", "id", "naam", "code", "niveau", "actief", "metadata"],
         gts)
    copy(cur, "laden.staging_relaties", ["levering_id", "regel", "indicator_uuid", "gebiedstype_id"],
         [(lid, r["_regel"], r["indicator_uuid"], r["gebiedstype_id"]) for r in uit["relaties"]
          if r.get("indicator_uuid") and r.get("gebiedstype_id")])


def db_controles(cur, ctx: Context, fouten: Fouten) -> None:
    p = {"lv": ctx.levering_id, "ds": ctx.dataset_id}
    sql_fouten(cur, fouten, """
        SELECT s.regel, count(*) OVER () AS totaal FROM laden.staging_gebiedstypen s
        WHERE s.levering_id = %(lv)s AND s.code IS NOT NULL
          AND EXISTS (SELECT 1 FROM public.gebiedstypes t WHERE t.code = s.code AND t.id <> s.id)
        ORDER BY s.regel LIMIT 1000""", p, "dubbele-sleutel", "gebiedstypen", "code",
        "code is al in gebruik bij een ander gebiedstype")
    sql_fouten(cur, fouten, """
        SELECT s.regel, count(*) OVER () AS totaal FROM laden.staging_indicatoren s
        WHERE s.levering_id = %(lv)s AND s.code IS NOT NULL
          AND EXISTS (SELECT 1 FROM public.indicatoren i WHERE i.code = s.code AND i.uuid <> s.uuid)
        ORDER BY s.regel LIMIT 1000""", p, "dubbele-sleutel", "indicatoren", "code",
        "code is al in gebruik bij een andere indicator")
    # Relaties die deze dataset eerder leverde en nu ontbreken, terwijl er nog waarden aan hangen
    cur.execute("""
        SELECT split_part(o.sleutel, '|', 1) AS ind, split_part(o.sleutel, '|', 2) AS gt
        FROM laden.dataset_objecten o
        WHERE o.dataset_id = %(ds)s AND o.soort = 'relatie'
          AND NOT EXISTS (SELECT 1 FROM laden.staging_relaties s WHERE s.levering_id = %(lv)s
                          AND s.indicator_uuid::text || '|' || s.gebiedstype_id::text = o.sleutel)
          AND EXISTS (SELECT 1 FROM public.gebied_data d JOIN public.gebieden g ON g.id = d.gebied_id
                      WHERE d.indicator_uuid::text = split_part(o.sleutel, '|', 1)
                        AND g.gebiedstype_id::text = split_part(o.sleutel, '|', 2))
        LIMIT 1000""", p)
    for r in cur.fetchall():
        fouten.voeg(Fout("relatie-in-gebruik", "relatie indicator × gebiedstype ontbreekt in de levering, maar er "
                         f"hangen nog waarden aan (indicator {r['ind']}, gebiedstype {r['gt']})", "relaties"))


def publiceer(cur, ctx: Context) -> dict:
    p = {"lv": ctx.levering_id, "ds": ctx.dataset_id}
    cur.execute("SELECT count(*) AS n FROM laden.dataset_objecten WHERE dataset_id = %(ds)s", p)
    vorig = cur.fetchone()["n"]
    cur.execute("""
        INSERT INTO public.gebiedstypes AS t (id, naam, code, niveau, actief, metadata)
        SELECT s.id, s.naam, s.code, s.niveau, coalesce(s.actief, true), s.metadata
        FROM laden.staging_gebiedstypen s WHERE s.levering_id = %(lv)s
        ON CONFLICT (id) DO UPDATE SET
            naam = EXCLUDED.naam,
            code = coalesce(EXCLUDED.code, t.code),
            niveau = coalesce(EXCLUDED.niveau, t.niveau),
            actief = EXCLUDED.actief,
            metadata = coalesce(t.metadata, '{}'::jsonb) || coalesce(EXCLUDED.metadata, '{}'::jsonb)""", p)
    n_gt = cur.rowcount
    cur.execute("""
        UPDATE public.indicatoren i SET
            naam = s.naam,
            code = coalesce(s.code, i.code),
            omschrijving = coalesce(s.omschrijving, i.omschrijving),
            eenheid = coalesce(s.eenheid, i.eenheid),
            score_type = coalesce(s.score_type, i.score_type),
            min_waarde = coalesce(s.min_waarde, i.min_waarde),
            max_waarde = coalesce(s.max_waarde, i.max_waarde),
            status = coalesce(s.status, i.status),
            begingeldigheid = coalesce(s.begingeldigheid, i.begingeldigheid),
            eindgeldigheid = s.eindgeldigheid,
            bron = coalesce(s.bron, i.bron)
        FROM laden.staging_indicatoren s
        WHERE s.levering_id = %(lv)s AND s.uuid = i.uuid""", p)
    n_bijgewerkt = cur.rowcount
    cur.execute("""
        INSERT INTO public.indicatoren (uuid, naam, code, omschrijving, eenheid, score_type, min_waarde,
                                        max_waarde, status, begingeldigheid, eindgeldigheid, bron)
        SELECT s.uuid, s.naam, s.code, s.omschrijving, s.eenheid, coalesce(s.score_type, '+/+'), s.min_waarde,
               s.max_waarde, coalesce(s.status, 'O'), s.begingeldigheid, s.eindgeldigheid, s.bron
        FROM laden.staging_indicatoren s
        WHERE s.levering_id = %(lv)s AND NOT EXISTS (SELECT 1 FROM public.indicatoren i WHERE i.uuid = s.uuid)""", p)
    n_ind = n_bijgewerkt + cur.rowcount
    nieuw_ind = cur.rowcount
    # Eerder geleverd, nu niet meer in de set
    cur.execute("""
        UPDATE public.indicatoren i SET eindgeldigheid = now()
        FROM laden.dataset_objecten o
        WHERE o.dataset_id = %(ds)s AND o.soort = 'indicator' AND o.sleutel = i.uuid::text
          AND i.eindgeldigheid IS NULL
          AND NOT EXISTS (SELECT 1 FROM laden.staging_indicatoren s WHERE s.levering_id = %(lv)s AND s.uuid = i.uuid)""", p)
    beeindigd = cur.rowcount
    cur.execute("""
        UPDATE public.gebiedstypes t SET actief = false
        FROM laden.dataset_objecten o
        WHERE o.dataset_id = %(ds)s AND o.soort = 'gebiedstype' AND o.sleutel = t.id::text
          AND NOT EXISTS (SELECT 1 FROM laden.staging_gebiedstypen s WHERE s.levering_id = %(lv)s AND s.id = t.id)""", p)
    cur.execute("""
        DELETE FROM public.indicator_gebiedstype_relaties r
        USING laden.dataset_objecten o
        WHERE o.dataset_id = %(ds)s AND o.soort = 'relatie'
          AND o.sleutel = r.indicator_uuid::text || '|' || r.gebiedstype_id::text
          AND NOT EXISTS (SELECT 1 FROM laden.staging_relaties s WHERE s.levering_id = %(lv)s
                          AND s.indicator_uuid = r.indicator_uuid AND s.gebiedstype_id = r.gebiedstype_id)""", p)
    vervallen = cur.rowcount
    cur.execute("""
        INSERT INTO public.indicator_gebiedstype_relaties (indicator_uuid, gebiedstype_id)
        SELECT DISTINCT s.indicator_uuid, s.gebiedstype_id FROM laden.staging_relaties s WHERE s.levering_id = %(lv)s
        ON CONFLICT DO NOTHING""", p)
    cur.execute("SELECT count(*) AS n FROM laden.staging_relaties WHERE levering_id = %(lv)s", p)
    n_rel = cur.fetchone()["n"]
    # De set van deze dataset vastleggen
    cur.execute("DELETE FROM laden.dataset_objecten WHERE dataset_id = %(ds)s", p)
    cur.execute("""
        INSERT INTO laden.dataset_objecten (dataset_id, soort, sleutel)
        SELECT %(ds)s, 'indicator', uuid::text FROM laden.staging_indicatoren WHERE levering_id = %(lv)s
        UNION SELECT %(ds)s, 'gebiedstype', id::text FROM laden.staging_gebiedstypen WHERE levering_id = %(lv)s
        UNION SELECT %(ds)s, 'relatie', indicator_uuid::text || '|' || gebiedstype_id::text
              FROM laden.staging_relaties WHERE levering_id = %(lv)s""", p)
    for t in ("staging_indicatoren", "staging_gebiedstypen", "staging_relaties"):
        cur.execute(f"DELETE FROM laden.{t} WHERE levering_id = %(lv)s", p)
    totaal = n_ind + n_gt + n_rel
    plausibel(ctx.laadprofiel, totaal, vorig)
    return {"gepubliceerd": totaal, "vervangen": vorig, "beeindigd": beeindigd, "relatiesVervallen": vervallen,
            "nieuweIndicatoren": nieuw_ind,
            "_aantal_regels": totaal, "_levering_ids": [ctx.levering_id]}
