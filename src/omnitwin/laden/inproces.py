"""
Laad-API in-process (zelfde functies, zonder HTTP en zonder token)
==================================================================
Voor de eerste installatie (`db-init`): dan draaien backend en Keycloak nog niet, maar moeten de
use cases wel via de laadstraat geladen worden (#236; RFC #182: "HTTP of dezelfde functie
in-process"). Zelfde registratie, opslag, idempotentie en verwerking als de HTTP-ingang
(`omnitwin.routers.laden`), alleen synchroon en met de verbinding van de databasebeheerder.

Dezelfde interface als `omnitwin.usecases.LaadApi` (`registreer`, `lever`, `beheer`), zodat de
use-case-uitvoerder hem met `installeer --inproces` kan gebruiken. Alleen voor wie al toegang
tot de database heeft (dezelfde rechten als `load_sample.py`); geen nieuwe ingang van buiten.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

CLIENT = "inproces"
MEDIATYPE = {
    ".zip": "application/zip",
    ".gpkg": "application/geopackage+sqlite3",
    ".csv": "text/csv",
    ".json": "application/json",
}
HTTP = {"gepubliceerd": 201, "gevalideerd": 201, "afgekeurd": 422, "mislukt": 500}


class InprocesLaadApi:
    """De laad-API als functies: registreren en leveren zonder HTTP."""

    basis = "inproces"

    def __init__(self, client: str = CLIENT):
        self.client = client
        self.s = None  # geen HTTP-sessie: controles van het type api/aantal draaien alleen tegen een installatie

    def registreer(self, registratie: dict) -> dict:
        from omnitwin.laden.problemen import Probleem
        from omnitwin.routers import laden as r

        try:
            r._registratie_fouten(registratie)
            with r.transactie() as cur:
                bestaat = r._haal_dataset(cur, registratie["id"]) is not None
            return r._db_vervang(registratie["id"], registratie) if bestaat else r._db_registreer(registratie)
        except Probleem as p:
            raise RuntimeError(f"registratie {registratie['id']}: {p.code}: {p.detail}") from p

    def lever(self, ds_id: str, pad, route: str = "laden", alleen_valideren: bool = False) -> dict:
        import hashlib

        from omnitwin.laden import laadstraat, opslag
        from omnitwin.laden.problemen import Probleem
        from omnitwin.routers import laden as r

        if route != "laden":
            return {
                "http": 501,
                "status": "overgeslagen",
                "melding": f"route {route} kan niet met --inproces: installeer via de laad-API "
                "(HTTP) met een machineclient",
            }
        pad = Path(pad)
        mt = MEDIATYPE.get(pad.suffix) or mimetypes.guess_type(pad.name)[0] or "application/octet-stream"
        sleutel = f"{ds_id}-{hashlib.sha256(pad.read_bytes()).hexdigest()[:16]}"
        with open(pad, "rb") as f:
            ontvangen = opslag.ontvang_bestand(f, r._limiet(mt))
        try:
            lv, nieuw = r._db_nieuwe_levering(
                ds_id,
                ontvangen,
                mt,
                opslag.veilige_bestandsnaam(pad.name, mt),
                sleutel,
                alleen_valideren,
                self.client,
                None,
            )
        except Probleem as p:
            return {"http": p.status, "status": p.code, "melding": p.detail}
        finally:
            opslag.verwijder_tijdelijk(ontvangen)
        if nieuw:
            laadstraat.verwerk(str(lv["id"]))
        lv, fouten = r._db_levering(str(lv["id"]))
        return {"http": HTTP.get(lv["status"], 202), **r.levering_uit(lv, fouten)}

    def beheer(self, pad_api: str, bestand) -> dict:
        """Inrichting (Kompasprofielen, externe kaartlagen) via `omnitwin.laden.beheer`; andere soorten:
        overgeslagen (501)."""
        from omnitwin.laden import beheer

        return beheer.voer_uit(pad_api, bestand)
