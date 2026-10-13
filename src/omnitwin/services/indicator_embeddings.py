"""
Embeddings van indicatoren berekenen en bijwerken (#139, #233).

Per actieve indicator wordt één tekst geëmbed (services/zoektaal.py, indicator_tekst):
naam, kompaspad (titel / thema / onderdeel uit Kompas-configuratie 1), eenheid, de synoniemen
uit db/stuurdata/synoniemen.json en de beste beschrijving (ontologische_beschrijving >
beschrijving_ai > omschrijving). In indicator_embeddings staat naast de vector de tekst_hash
(SHA-256 van model, revisie en tekst, migratie V028). Een embedding wordt (opnieuw) berekend
als hij ontbreekt of als de hash afwijkt: nieuw model, nieuwe synoniemen, gewijzigde naam.

Gebruik:
- db-init: scripts/ai/genereer_embeddings.py (alle actieve indicatoren);
- na een levering met nieuwe of gewijzigde indicatordefinities (laad-API, profiel
  'definities'): herbereken_embeddings(db, indicator_uuids) na de commit van de publicatie.
  Alleen wat gewijzigd is wordt berekend; het model wordt alleen geladen als er iets te doen is.
"""

import hashlib
import logging
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text

from omnitwin.services import embedding_model, zoektaal

logger = logging.getLogger(__name__)


def tekst_hash(tekst: str) -> str:
    """Hash van model, revisie en tekst: verandert een van drieën, dan opnieuw berekenen."""
    return hashlib.sha256(
        f"{embedding_model.MODEL_ID}@{embedding_model.MODEL_REVISIE}\n{tekst}".encode("utf-8")
    ).hexdigest()


def lees_indicatoren(
    db, indicator_uuids: Optional[Iterable[str]] = None, alleen_goedgekeurd: bool = False
) -> List[Dict[str, Any]]:
    """Actieve indicatoren met de velden voor de tekst en de huidige hash."""
    filters = ["i.is_actief = true"]
    params: Dict[str, Any] = {}
    if indicator_uuids is not None:
        filters.append("CAST(i.uuid AS text) = ANY(:uuids)")
        params["uuids"] = [str(u) for u in indicator_uuids]
    if alleen_goedgekeurd:
        filters.append("i.ontologie_status = 'goedgekeurd_mens'")
    rows = db.execute(
        text(f"""
        SELECT CAST(i.uuid AS text), i.naam,
               COALESCE(NULLIF(i.ontologische_beschrijving, ''), NULLIF(i.beschrijving_ai, ''),
                        NULLIF(i.omschrijving, '')) AS beschrijving,
               COALESCE(vkh.titel_naam, i.categorie), vkh.thema_naam, vkh.onderdeel_naam, i.eenheid,
               e.tekst_hash, e.model_naam
        FROM indicatoren i
        LEFT JOIN v_kompas_hierarchie vkh ON vkh.indicator_uuid = i.uuid AND vkh.config_id = 1
        LEFT JOIN indicator_embeddings e ON e.indicator_uuid = i.uuid
        WHERE {" AND ".join(filters)}
        ORDER BY i.naam
    """),
        params,
    ).fetchall()
    uit, gezien = [], set()
    for r in rows:
        if r[0] in gezien:  # een indicator kan in de view meer dan eens voorkomen
            continue
        gezien.add(r[0])
        uit.append(
            {
                "uuid": r[0],
                "naam": r[1],
                "beschrijving": r[2],
                "kompaspad": [r[3], r[4], r[5]],
                "eenheid": r[6],
                "tekst_hash": r[7],
                "model_naam": r[8],
            }
        )
    return uit


def teksten(indicatoren: List[Dict[str, Any]], begrippen=None) -> List[str]:
    begrippen = zoektaal.laad_begrippen() if begrippen is None else begrippen
    return [
        zoektaal.indicator_tekst(
            i["naam"], i["beschrijving"], i["kompaspad"], i["eenheid"], zoektaal.synoniemen_van(i["naam"], begrippen)
        )
        for i in indicatoren
    ]


def herbereken_embeddings(
    db,
    indicator_uuids: Optional[Iterable[str]] = None,
    opnieuw: bool = False,
    alleen_goedgekeurd: bool = False,
    model=None,
) -> Dict[str, int]:
    """
    Berekent de embeddings van nieuwe of gewijzigde actieve indicatoren en commit.

    indicator_uuids: alleen deze indicatoren (None = alle actieve)
    opnieuw:         ook als de hash gelijk is
    model:           een geladen SentenceTransformer (anders embedding_model.gedeeld_model())

    Geeft {"berekend": n, "ongewijzigd": m}. Gooit ModelNietBeschikbaar als er iets te
    berekenen is en het model ontbreekt; de aanroeper beslist of dat een fout is.
    """
    indicatoren = lees_indicatoren(db, indicator_uuids, alleen_goedgekeurd)
    alle_teksten = teksten(indicatoren)
    te_doen = [(i, t, tekst_hash(t)) for i, t in zip(indicatoren, alle_teksten)]
    te_doen = [
        (i, t, h)
        for i, t, h in te_doen
        if opnieuw or i["tekst_hash"] != h or i["model_naam"] != embedding_model.MODEL_NAAM
    ]
    resultaat = {"berekend": 0, "ongewijzigd": len(indicatoren) - len(te_doen)}
    if not te_doen:
        return resultaat

    model = model or embedding_model.gedeeld_model()
    vectoren = model.encode(
        [embedding_model.TEKST_VOORVOEGSEL + t for _, t, _ in te_doen],
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    sql = text("""
        INSERT INTO indicator_embeddings (indicator_uuid, embedding, model_naam, tekst_hash)
        VALUES (CAST(:uuid AS uuid), CAST(:emb AS vector), :model, :hash)
        ON CONFLICT (indicator_uuid) DO UPDATE
        SET embedding = EXCLUDED.embedding, model_naam = EXCLUDED.model_naam,
            tekst_hash = EXCLUDED.tekst_hash, updated_at = CURRENT_TIMESTAMP
    """)
    for (ind, _, h), v in zip(te_doen, vectoren):
        db.execute(sql, {"uuid": ind["uuid"], "emb": v.tolist(), "model": embedding_model.MODEL_NAAM, "hash": h})
    db.commit()
    resultaat["berekend"] = len(te_doen)
    logger.info("Embeddings: %s berekend, %s ongewijzigd", resultaat["berekend"], resultaat["ongewijzigd"])
    return resultaat
