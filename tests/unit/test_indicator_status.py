"""Unit tests voor indicator actief/inactief beheer (#526)."""

import uuid
from unittest.mock import MagicMock

import pytest

from omnitwin.routers.admin import IndicatorUpdate, get_indicatoren, update_indicator

pytestmark = pytest.mark.unit


def test_indicator_update_schema_accepts_is_actief():
    """IndicatorUpdate pydantic model ondersteunt is_actief (#526)."""
    update_true = IndicatorUpdate(is_actief=True)
    assert update_true.is_actief is True

    update_false = IndicatorUpdate(is_actief=False)
    assert update_false.is_actief is False

    update_none = IndicatorUpdate()
    assert update_none.is_actief is None


def test_update_indicator_past_is_actief_toe():
    """update_indicator bouwt SQL UPDATE inclusief is_actief en commit (#526)."""
    test_uuid = uuid.uuid4()
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    # Mock get_indicator returning a dict
    mock_row = [
        str(test_uuid),
        "Test Indicator",
        "Omschrijving",
        "CBS",
        "%",
        "+/+",
        1,
        "Standaard",
        None,
        "draft",
        None,
        None,
        None,
        False,
        None,
        "hoger_is_beter",
        None,
        None,
        None,
        None,
        None,
        None,
        "hoger_is_beter",
    ]
    mock_db.execute.return_value.fetchone.return_value = mock_row

    data = IndicatorUpdate(is_actief=False)
    update_indicator(uuid=test_uuid, data=data, db=mock_db)

    # Verifieer dat de update query is uitgevoerd met is_actief
    first_call_args = mock_db.execute.call_args_list[0]
    query_text = str(first_call_args[0][0].text)
    params = first_call_args[0][1]

    assert "is_actief = :is_actief" in query_text
    assert params["is_actief"] is False
    assert params["uuid"] == str(test_uuid)
    assert mock_db.commit.called


def test_get_indicatoren_filtert_op_is_actief():
    """get_indicatoren voegt i.is_actief filter toe aan query en count_query (#526)."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []
    mock_db.execute.return_value.scalar.return_value = 0

    # Filter is_actief = True
    get_indicatoren(is_actief=True, db=mock_db)
    query_calls = mock_db.execute.call_args_list

    main_query = str(query_calls[0][0][0].text)
    main_params = query_calls[0][0][1]
    count_query = str(query_calls[1][0][0].text)
    count_params = query_calls[1][0][1]

    assert "AND i.is_actief = :is_actief" in main_query
    assert main_params["is_actief"] is True
    assert "AND i.is_actief = :is_actief" in count_query
    assert count_params["is_actief"] is True

    # Zonder filter: geen is_actief in query
    mock_db.reset_mock()
    get_indicatoren(is_actief=None, db=mock_db)
    query_calls_none = mock_db.execute.call_args_list
    main_query_none = str(query_calls_none[0][0][0].text)
    assert "AND i.is_actief = :is_actief" not in main_query_none


def test_migratie_v052_bevat_is_actief_filter():
    """Migratie V052 bevat het filter i.is_actief = true in beide branches (#526)."""
    with open("db/migraties/V052__filter_inactieve_indicatoren_stats.sql") as f:
        inhoud = f.read()

    assert "WHERE i.status IN ('O', 'C') AND i.is_actief = true" in inhoud
    # Moet in beide branches voorkomen (met en zonder p_gebiedstype_id)
    assert inhoud.count("WHERE i.status IN ('O', 'C') AND i.is_actief = true") == 2
