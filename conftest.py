"""
conftest.py — pytest configuratie op project-niveau.

Bestanden die een live database of externe services vereisen worden
uitgesloten van collectie in CI (geen DB beschikbaar).
Ze draaien alleen als de `integration` of `e2e` marker expliciet wordt meegegeven
én de juiste omgeving aanwezig is.
"""
collect_ignore = [
    "tests/test_zscore.py",          # integration: vereist live PostgreSQL
    "tests/test_canvas.py",          # e2e: vereist draaiende server + Playwright
    "tests/test_deelgebied_report.py",  # integration: vereist live PostgreSQL + src module
]
