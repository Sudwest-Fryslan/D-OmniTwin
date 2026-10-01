"""
conftest.py — pytest configuratie op project-niveau.

Elke test hoort bij precies één soort, met een marker (zie pyproject.toml):
`unit` (CI-job Unit Tests), `integration` en `e2e` (CI-job Integratietests, tegen
een verse stack) of `llm` (alleen handmatig, LLM_TEST=1). Een test zonder een van
die markers draait in geen enkele CI-job; daarom faalt de collectie dan (#202).
De E2E-tests (tests/e2e) krijgen hun marker in tests/e2e/conftest.py en slaan
zichzelf over als Playwright niet geïnstalleerd is.
"""
import pytest

SOORTEN = ("unit", "integration", "e2e", "llm")


# Gewone hookimpl (geen trylast): pytest roept conftest-hooks in omgekeerde volgorde van
# registratie aan, dus eerst tests/e2e/conftest.py (zet de e2e-marker), dan deze, en pas
# daarna de deselectie van `-m`. Zo vangt ook `pytest -m unit` tests zonder marker.
def pytest_collection_modifyitems(config, items):
    zonder = [item.nodeid for item in items
              if not any(item.get_closest_marker(soort) for soort in SOORTEN)]
    if zonder:
        raise pytest.UsageError(
            "Tests zonder marker (" + "/".join(SOORTEN) + "), die in geen enkele CI-job draaien:\n  "
            + "\n  ".join(zonder)
        )
