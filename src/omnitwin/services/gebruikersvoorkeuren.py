"""
Favorieten en laatste kaartpositie per ingelogde gebruiker (#258)
================================================================
Tabellen `gebruiker_voorkeuren` en `gebruiker_favorieten` (V035). Sleutel: `eigenaar`.

- Keycloak (OIDC-sessie of bearer-token): de `sub` van de gebruiker.
- Lokaal account (sessie zonder Keycloak, of noodtoegang): `lokaal:<users.id>`.
- Een script met X-Admin-Key is geen persoon: geen voorkeuren.

Alleen die sleutel wordt bewaard (geen naam of e-mail). Elke aanroep zet `laatst_gebruikt`; de
dagelijkse opruimtaak verwijdert na BEWAAR_DAGEN zonder gebruik de voorkeuren en favorieten.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from omnitwin.fouten import GebruikersFout

BEWAAR_DAGEN = 365
MAX_FAVORIETEN = 50
MAX_GEBIEDEN = 2000
MAX_NAAM = 80
GEBIED_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")

# Kaartpositie: alleen deze velden, binnen redelijke grenzen
POSITIE_GRENZEN = {
    "longitude": (-180.0, 180.0),
    "latitude": (-85.0, 85.0),
    "zoom": (0.0, 24.0),
    "pitch": (0.0, 85.0),
    "bearing": (-360.0, 360.0),
}


def eigenaar_van(gebruiker: Optional[Dict[str, Any]]) -> Optional[str]:
    """De sleutel van een ingelogde persoon, of None (anoniem of een script)."""
    if not gebruiker:
        return None
    soort = gebruiker.get("type")
    if soort in ("oidc", "bearer"):
        sub = gebruiker.get("onderwerp") or gebruiker.get("user_id")
        return str(sub) if sub else None
    if soort == "session" and gebruiker.get("user_id") is not None:
        return f"lokaal:{gebruiker['user_id']}"
    return None


def controleer_positie(positie: Dict[str, Any]) -> Dict[str, float]:
    uit: Dict[str, float] = {}
    for veld, (laag, hoog) in POSITIE_GRENZEN.items():
        waarde = positie.get(veld)
        if waarde is None:
            if veld in ("longitude", "latitude", "zoom"):
                raise GebruikersFout(f"Kaartpositie zonder {veld}.")
            continue
        try:
            getal = float(waarde)
        except (TypeError, ValueError):
            raise GebruikersFout(f"Kaartpositie: {veld} is geen getal.")
        if math.isnan(getal) or not laag <= getal <= hoog:
            raise GebruikersFout(f"Kaartpositie: {veld} buiten bereik.")
        uit[veld] = round(getal, 6)
    return uit


def controleer_favoriet(naam: str, gebied_ids: List[str]) -> tuple[str, List[str]]:
    naam = (naam or "").strip()
    if not 1 <= len(naam) <= MAX_NAAM:
        raise GebruikersFout(f"Geef de favoriet een naam van 1 tot {MAX_NAAM} tekens.")
    ids: List[str] = []
    for g in gebied_ids or []:
        g = str(g).strip()
        if not GEBIED_ID.match(g):
            raise GebruikersFout("Ongeldige gebied-id in de favoriet.")
        if g not in ids:
            ids.append(g)
    if not ids:
        raise GebruikersFout("Een favoriet heeft minstens één gebied.")
    if len(ids) > MAX_GEBIEDEN:
        raise GebruikersFout(f"Te veel gebieden in één favoriet: maximaal {MAX_GEBIEDEN}.")
    return naam, ids


def _favoriet(r) -> Dict[str, Any]:
    return {
        "id": str(r["id"]),
        "naam": r["naam"],
        "gebiedstypeId": str(r["gebiedstype_id"]) if r["gebiedstype_id"] else None,
        "gebiedIds": list(r["gebied_ids"]),
        "aangemaakt": r["aangemaakt"].isoformat(),
        "gewijzigd": r["gewijzigd"].isoformat(),
    }


class Voorkeuren:
    """Voorkeuren van één eigenaar. Elke methode raakt `laatst_gebruikt` aan en commit."""

    def __init__(self, db, eigenaar: str):
        self.db = db
        self.eigenaar = eigenaar

    def _raak_aan(self) -> None:
        self.db.execute(
            text("""
            INSERT INTO gebruiker_voorkeuren (eigenaar) VALUES (:e)
            ON CONFLICT (eigenaar) DO UPDATE SET laatst_gebruikt = now()
        """),
            {"e": self.eigenaar},
        )

    def instellingen(self) -> Dict[str, Any]:
        self._raak_aan()
        positie = self.db.execute(
            text("SELECT kaartpositie FROM gebruiker_voorkeuren WHERE eigenaar = :e"), {"e": self.eigenaar}
        ).scalar()
        self.db.commit()
        return {"kaartpositie": positie}

    def zet_instellingen(self, kaartpositie: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        positie = controleer_positie(kaartpositie) if kaartpositie is not None else None
        self._raak_aan()
        self.db.execute(
            text("UPDATE gebruiker_voorkeuren SET kaartpositie = CAST(:p AS jsonb) WHERE eigenaar = :e"),
            {"p": json.dumps(positie) if positie is not None else None, "e": self.eigenaar},
        )
        self.db.commit()
        return {"kaartpositie": positie}

    def favorieten(self) -> List[Dict[str, Any]]:
        self._raak_aan()
        rijen = (
            self.db.execute(
                text("""
            SELECT id, naam, gebiedstype_id, gebied_ids, aangemaakt, gewijzigd FROM gebruiker_favorieten
            WHERE eigenaar = :e ORDER BY lower(naam)
        """),
                {"e": self.eigenaar},
            )
            .mappings()
            .all()
        )
        self.db.commit()
        return [_favoriet(r) for r in rijen]

    def bewaar_favoriet(self, naam: str, gebied_ids: List[str], gebiedstype_id: Optional[str]) -> tuple[Dict, bool]:
        """Nieuw, of een bestaande met dezelfde naam vervangen. (favoriet, nieuw?)"""
        naam, ids = controleer_favoriet(naam, gebied_ids)
        self._raak_aan()
        bestaat = (
            self.db.execute(
                text("SELECT 1 FROM gebruiker_favorieten WHERE eigenaar = :e AND naam = :n"),
                {"e": self.eigenaar, "n": naam},
            ).first()
            is not None
        )
        if not bestaat:
            aantal = self.db.execute(
                text("SELECT count(*) FROM gebruiker_favorieten WHERE eigenaar = :e"), {"e": self.eigenaar}
            ).scalar()
            if aantal >= MAX_FAVORIETEN:
                self.db.rollback()
                raise GebruikersFout(f"Maximaal {MAX_FAVORIETEN} favorieten; verwijder er eerst een.")
        r = (
            self.db.execute(
                text("""
            INSERT INTO gebruiker_favorieten (eigenaar, naam, gebiedstype_id, gebied_ids)
            VALUES (:e, :n, CAST(:gt AS uuid), CAST(:ids AS text[]))
            ON CONFLICT (eigenaar, naam) DO UPDATE
               SET gebiedstype_id = EXCLUDED.gebiedstype_id, gebied_ids = EXCLUDED.gebied_ids, gewijzigd = now()
            RETURNING id, naam, gebiedstype_id, gebied_ids, aangemaakt, gewijzigd
        """),
                {"e": self.eigenaar, "n": naam, "gt": gebiedstype_id, "ids": ids},
            )
            .mappings()
            .first()
        )
        self.db.commit()
        return _favoriet(r), not bestaat

    def verwijder_favoriet(self, favoriet_id: str) -> bool:
        """Alleen een eigen favoriet; een andere (of onbekende) geeft False."""
        self._raak_aan()
        n = self.db.execute(
            text("DELETE FROM gebruiker_favorieten WHERE id = CAST(:id AS uuid) AND eigenaar = :e"),
            {"id": favoriet_id, "e": self.eigenaar},
        ).rowcount
        self.db.commit()
        return n > 0


def ruim_op(conn, dagen: int = BEWAAR_DAGEN) -> int:
    """Voorkeuren (en via de cascade de favorieten) zonder gebruik in `dagen` dagen verwijderen."""
    n = conn.execute(
        text("DELETE FROM gebruiker_voorkeuren WHERE laatst_gebruikt < now() - make_interval(days => :d)"),
        {"d": int(dagen)},
    ).rowcount
    conn.commit()
    return n
