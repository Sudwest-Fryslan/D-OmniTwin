"""
Unit tests voor de terugmeldvoorziening (#311): validatie, context, honeypot, rate limiting en AVG.
"""

import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from omnitwin.fouten import GebruikersFout
from omnitwin.grenzen import Limiet, beperk_meldingen
from omnitwin.routers.meldingen import MeldingInvoer, MeldingWijziging, meld
from omnitwin.services import meldingen as meldingen_service

pytestmark = pytest.mark.unit


def test_context_validatie_filtert_onbekende_sleutels_en_kapt_af():
    ruw = {
        "pagina": "kompas",
        "indicator_id": "armoede_pct",
        "vraag": "A" * 500,  # moet ingekort worden naar 300
        "resultaat": "B" * 800,  # moet ingekort worden naar 600
        "onbekend": "gevaarlijke_data",
        "gebied_ids": ["BU001", "BU002"],
    }
    gevalideerd = meldingen_service.valideer_context(ruw)

    assert "onbekend" not in gevalideerd
    assert gevalideerd["pagina"] == "kompas"
    assert gevalideerd["indicator_id"] == "armoede_pct"
    assert len(gevalideerd["vraag"]) == 300
    assert len(gevalideerd["resultaat"]) == 600
    assert gevalideerd["gebied_ids"] == ["BU001", "BU002"]


def test_context_validatie_weigert_enorme_payload():
    ruw = {
        "pagina": "kompas",
        "gebied_ids": ["BU" + "X" * 40 for _ in range(500)],  # overschrijdt 10 KB
    }
    # Zelfs na truncatie van de lijst kan een grote JSON geconstrueerd worden
    grote_string = "X" * 200
    grote_context = {f"k_{i}": grote_string for i in range(100)}
    # Alleen toegestane sleutels testen die heel groot zijn
    grote_context = {"vraag": "A" * 300, "resultaat": "B" * 600}
    # Mock json.dumps encode lengte > 10240
    with patch("omnitwin.services.meldingen.json.dumps", return_value="X" * 10500):
        with pytest.raises(GebruikersFout, match="10 KB"):
            meldingen_service.valideer_context(grote_context)


def test_melding_invoer_validatie_pydantic():
    # Geldige invoer
    invoer = MeldingInvoer(
        type="data",
        onderwerp="Verkeerde definitie",
        toelichting="De waarde voor 2024 lijkt niet te kloppen.",
        melder_email="inwoner@example.org",
    )
    assert invoer.type == "data"
    assert invoer.melder_email == "inwoner@example.org"

    # Ongeldig type
    with pytest.raises(ValidationError):
        MeldingInvoer(
            type="ongeldig",  # type: ignore
            onderwerp="Test",
            toelichting="Test toelichting",
        )

    # Ongeldig e-mailadres
    with pytest.raises(ValidationError):
        MeldingInvoer(
            type="systeem",
            onderwerp="Test",
            toelichting="Test toelichting",
            melder_email="geen-geldig-email",
        )

    # Te lang onderwerp (>120 tekens)
    with pytest.raises(ValidationError):
        MeldingInvoer(
            type="systeem",
            onderwerp="A" * 121,
            toelichting="Test toelichting",
        )


def test_honeypot_wijst_stil_af_zonder_database_insert():
    mock_db = MagicMock()
    invoer = MeldingInvoer(
        type="systeem",
        onderwerp="Spambot aanval",
        toelichting="Koop nu crypto",
        website="https://spam.example.com",  # honeypot gevuld!
    )

    with patch("omnitwin.services.meldingen.maak_melding") as mock_maak:
        res = meld(invoer, db=mock_db)
        assert res["status"] == "ontvangen"
        assert "id" in res
        mock_maak.assert_not_called()  # database is NIET geraakt


def test_rate_limit_blokkeert_na_maximum():
    limiet = Limiet(maximum=2, venster=60.0)
    ip = "192.0.2.1"

    assert limiet.probeer(ip) == 0  # 1e verzoek: toegestaan
    assert limiet.probeer(ip) == 0  # 2e verzoek: toegestaan
    wacht = limiet.probeer(ip)  # 3e verzoek: geblokkeerd!
    assert wacht > 0


def test_beperk_meldingen_dependency():
    mock_request = MagicMock()
    mock_request.client.host = "192.0.2.2"
    mock_request.headers.getlist.return_value = []

    # Reset limiet voor test IP
    from omnitwin import grenzen

    grenzen._meldingen_limiet.reset("192.0.2.2")

    for _ in range(10):
        beperk_meldingen(mock_request)

    # 11e verzoek moet HTTPException 429 geven
    with pytest.raises(HTTPException) as exc_info:
        beperk_meldingen(mock_request)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_avg_email_wissen_bij_afhandeling():
    mock_db = MagicMock()
    test_id = uuid.uuid4()

    mock_db.execute.return_value.mappings.return_value.first.side_effect = [
        # Eerste aanroep: haal_melding
        MagicMock(
            id=test_id,
            type="data",
            onderwerp="Foutje",
            toelichting="Uitleg",
            context={},
            melder_email="burger@example.com",
            status="in_behandeling",
            notitie_beheer=None,
            aangemaakt_op=None,
            bijgewerkt_op=None,
        ),
        # Tweede aanroep: update RETURNING
        MagicMock(
            id=test_id,
            type="data",
            onderwerp="Foutje",
            toelichting="Uitleg",
            context={},
            melder_email=None,  # gewist!
            status="afgehandeld",
            notitie_beheer="Opgelost",
            aangemaakt_op=None,
            bijgewerkt_op=None,
        ),
    ]

    res = meldingen_service.werk_melding_bij(
        db=mock_db,
        melding_id=test_id,
        status="afgehandeld",
        notitie_beheer="Opgelost",
        beheerder="admin_taeke",
    )

    assert res["status"] == "afgehandeld"
    assert res["melder_email"] is None

    # Controleer of SQL update 'melder_email = NULL' bevatte
    query_str = str(mock_db.execute.call_args_list[1][0][0])
    assert "melder_email = NULL" in query_str


def test_ruim_op_verwijdert_oude_meldingen():
    mock_conn = MagicMock()
    mock_conn.execute.return_value.rowcount = 4

    verwijderd = meldingen_service.ruim_op(mock_conn, dagen=365)
    assert verwijderd == 4
    mock_conn.commit.assert_called_once()
