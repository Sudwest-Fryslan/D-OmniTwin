"""
Integratietest: dashboardcijfers en het filter "alleen met data" (#246).

- Data-dekking telt alleen actieve indicatoren, dus nooit boven 100%.
- Metadata-compleetheid ook over de indicatoren met data (definities zonder levering drukken
  anders het getal).
- GET /api/admin/indicatoren?met_data=true geeft alleen indicatoren met minstens één waarde.

Draaien tegen een stack met sampledata:
    OMNITWIN_BASE_URL=http://localhost:8080 ADMIN_API_KEY=... pytest -m integration tests/integration/test_dashboard_met_data.py
"""
import os

import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60


@pytest.fixture(scope="module")
def beheerder():
    key = os.environ.get("ADMIN_API_KEY", "")
    if not key:
        pytest.skip("ADMIN_API_KEY nodig")
    h = {"X-Admin-Key": key}
    if requests.get(f"{BASE_URL}/api/admin/dashboard/stats", headers=h, timeout=TIMEOUT).status_code in (401, 403):
        pytest.skip("ADMIN_API_KEY wordt niet geaccepteerd")
    return h


def test_dashboard_dekking_en_metadata_met_data(beheerder):
    s = requests.get(f"{BASE_URL}/api/admin/dashboard/stats", headers=beheerder, timeout=TIMEOUT).json()
    assert 0 <= s["with_data_count"] <= s["total_indicators"]
    assert 0 <= s["with_data_pct"] <= 100
    assert 0 <= s["metadata_complete_met_data_count"] <= s["with_data_count"]
    assert 0 <= s["metadata_complete_met_data_pct"] <= 100
    assert s["metadata_complete_met_data_count"] <= s["metadata_complete_count"]


def test_indicatoren_filter_alleen_met_data(beheerder):
    url = f"{BASE_URL}/api/admin/indicatoren"
    alle = requests.get(url, params={"limit": 1}, headers=beheerder, timeout=TIMEOUT).json()
    met = requests.get(url, params={"limit": 1000, "met_data": "true"}, headers=beheerder, timeout=TIMEOUT).json()
    assert met["total"] <= alle["total"]
    assert met["total"] == len(met["indicatoren"])
    stats = requests.get(f"{BASE_URL}/api/admin/dashboard/stats", headers=beheerder, timeout=TIMEOUT).json()
    # met_data filtert niet op actief; het dashboard telt alleen actieve
    assert met["total"] >= stats["with_data_count"]
