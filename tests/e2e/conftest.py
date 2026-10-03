"""
Fixtures voor de browser-E2E-tests (Playwright, sync API).

Draait tegen een draaiende stack; zie tests/e2e/README.md voor het reproduceerbare
commando in de Playwright-container. Alle tests in deze map krijgen de `e2e`-marker.

Omgevingsvariabelen:
    OMNITWIN_BASE_URL   basis-URL via Traefik (standaard http://localhost)
    E2E_HEADED          "1" = browser zichtbaar (lokaal debuggen)
"""

import os
import re
from pathlib import Path

import pytest

try:
    from playwright.sync_api import expect, sync_playwright

    # Software-WebGL in de container is traag, op CI-runners zonder GPU nog trager:
    # ruimere standaardtimeout voor expect(), instelbaar via E2E_EXPECT_TIMEOUT_MS.
    expect.set_options(timeout=int(os.environ.get("E2E_EXPECT_TIMEOUT_MS", "15000")))
except ImportError:  # CI-unit-job heeft geen Playwright: map dan niet verzamelen
    sync_playwright = None
    collect_ignore_glob = ["test_*.py"]

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

# localStorage-vlaggen: welkomstmodal en contextuele tips overslaan, zodat ze
# geen klikken op de kaart onderscheppen. Tests die de onboarding zelf toetsen
# gebruiken `app_page_fresh`.
_SKIP_ONBOARDING = """
try {
  localStorage.setItem('omnitwin_welcomed', '1');
  for (const k of ['omnitwin_tt_indicator', 'omnitwin_tt_buurt', 'omnitwin_tt_kompas', 'omnitwin_tt_ai']) {
    localStorage.setItem(k, '1');
  }
} catch (e) {}
"""

# Gemeentefilter Súdwest-Fryslân bij de eerste paginalading (#236). Een verse installatie heeft
# alle CBS-buurten van Fryslân (931); in de container zonder GPU (SwiftShader) kost picking bij
# pointerdown dan meer dan de tap-drempel van deck.gl (250 ms) en wordt een echte klik geen klik.
# Met het filter staan er 155 buurten op de kaart, met alle testbuurten van de demo-use cases.
_TESTGEMEENTE = """
try {
  if (!sessionStorage.getItem('e2e-testgemeente')) {
    sessionStorage.setItem('e2e-testgemeente', '1');
    localStorage.setItem('omnitwin-gemeente', '1900');
  }
} catch (e) {}
"""

# Consolemeldingen die niets zeggen over de applicatie zelf (externe basiskaart).
_CONSOLE_RUIS = [
    re.compile(r"Failed to load resource", re.I),
    re.compile(r"tiles?\b|glyphs|sprite", re.I),
]


def pytest_collection_modifyitems(config, items):
    for item in items:
        if Path(str(item.fspath)).parent == Path(__file__).resolve().parent:
            item.add_marker(pytest.mark.e2e)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(
            headless=os.environ.get("E2E_HEADED") != "1",
            # WebGL (deck.gl/MapLibre) zonder GPU: software-rendering via SwiftShader
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
        )
        yield b
        b.close()


def _open(browser, request, skip_onboarding, reduced_motion=None):
    opties = {"reduced_motion": reduced_motion} if reduced_motion else {}
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="nl-NL", **opties)
    if skip_onboarding:
        context.add_init_script(_SKIP_ONBOARDING)
        context.add_init_script(_TESTGEMEENTE)
    page = context.new_page()
    page.set_default_timeout(20_000)

    fouten = []
    page.on("pageerror", lambda exc: fouten.append(f"pageerror: {exc}"))
    page.on(
        "console",
        lambda msg: fouten.append(f"console.error: {msg.text}")
        if msg.type == "error" and not any(p.search(msg.text) for p in _CONSOLE_RUIS)
        else None,
    )
    page.console_fouten = fouten

    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    # Klaar = deck.gl geïnitialiseerd, gebiedstypes en Kompas-configuraties geladen
    page.wait_for_function(
        "() => window.state && window.state.deckgl && window.kompasViz && window.kompasViz.currentConfigId"
        " && document.querySelectorAll('#gebiedstype-select option').length > 1",
        timeout=60_000,
    )

    yield page

    failed = any(getattr(request.node, f"rep_{w}", None) and getattr(request.node, f"rep_{w}").failed
                 for w in ("setup", "call"))
    if failed:
        ARTIFACTS.mkdir(exist_ok=True)
        naam = re.sub(r"[^\w.-]+", "_", request.node.nodeid.split("::")[-1])
        try:
            page.screenshot(path=str(ARTIFACTS / f"{naam}.png"), full_page=True)
            (ARTIFACTS / f"{naam}.console.txt").write_text("\n".join(fouten), encoding="utf-8")
        except Exception:
            pass
    context.close()


@pytest.fixture
def app_page(browser, request):
    """App geopend, onboarding overgeslagen."""
    yield from _open(browser, request, skip_onboarding=True)


@pytest.fixture
def app_page_reduced_motion(browser, request):
    """App geopend met de systeeminstelling 'minder beweging' (prefers-reduced-motion: reduce)."""
    yield from _open(browser, request, skip_onboarding=True, reduced_motion="reduce")


@pytest.fixture
def app_page_fresh(browser, request):
    """App geopend als nieuwe bezoeker (welkomstmodal zichtbaar)."""
    yield from _open(browser, request, skip_onboarding=False)
