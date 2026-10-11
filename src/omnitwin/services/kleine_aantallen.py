"""
Kleine aantallen (#325)
=======================
Eén plek voor de drempels rond kleine aantallen.

- **n-drempel** (standaard 10, instelbaar per instantie in `organisatie.n_drempel`):
  een waarde die op minder waarnemingen (`gebied_data.n`) rust, tonen we niet en
  telt niet mee. Niet op de kaart en in de tooltip, niet in het indicatorpaneel, de
  rapporten, de chat en de CSV, en niet in de referentiegroep van Z-score, percentiel
  en label. Een waarde zonder bekende n telt wel mee. In SQL: `is_kleine_aantallen(n)`
  en `kleine_aantallen_drempel()` (migratie V044); deze module leest dezelfde waarde.
- **minimum aantal gebieden** in de Z-scorereferentie (5): iets anders. Hebben minder
  gebieden een waarde in hetzelfde jaar, dan valt de Z-score terug op de recentste
  waarde per gebied (#155). Dat gaat over de grootte van de referentiegroep, niet over
  de betrouwbaarheid van één waarde.
"""

from typing import Optional

N_DREMPEL_STANDAARD = 10
MIN_GEBIEDEN_REFERENTIE = 5

# SQL-voorwaarde: de waarde rust niet op te weinig waarnemingen. {alias} = tabelalias met kolom n.
SQL_NIET_ONDERDRUKT = "NOT is_kleine_aantallen({alias}.n)"


def niet_onderdrukt_sql(alias: str = "gd") -> str:
    return SQL_NIET_ONDERDRUKT.format(alias=alias)


def drempel(db) -> int:
    """De n-drempel van deze instantie (organisatie.n_drempel), anders de standaard.

    Zonder database, of een database van vóór V044, geldt de standaard."""
    if db is None:
        return N_DREMPEL_STANDAARD
    from sqlalchemy import text

    try:
        with db.begin_nested():
            waarde = db.execute(text("SELECT kleine_aantallen_drempel()")).scalar()
    except Exception:
        return N_DREMPEL_STANDAARD
    return int(waarde) if waarde else N_DREMPEL_STANDAARD


def is_onderdrukt(n: Optional[int], drempel: int = N_DREMPEL_STANDAARD) -> bool:
    """True als n bekend is en onder de drempel ligt."""
    return n is not None and n < drempel
