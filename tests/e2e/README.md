# Browser-E2E-tests (Playwright)

Geautomatiseerde uitvoering van de functionele testcases uit
[`docs/testcases/`](../../docs/testcases/README.md) tegen een draaiende stack met de
sample dataset. Elke test verwijst in naam en docstring naar zijn TC-id
(`test_tc_01_001_...` = TC-01-001). Het overzicht per testcase staat in
[`docs/testcases/README.md`](../../docs/testcases/README.md#-automatisering).

| Bestand | Testcases |
|---|---|
| `test_kaartmodule.py` | TC-01-001, TC-01-002, TC-01-003 (+ kaart-export) |
| `test_kaartmodus.py` | TC-01-004 (kaartmodus percentielklasse / werkelijke waarde / uit, #255) |
| `test_kompas_detail.py` | TC-02-001, TC-02-002 |
| `test_integratie_e2e.py` | TC-06-001, TC-06-004 |
| `test_integratie_e2e.py` | TC-06-001 |
| `test_toegankelijkheid.py` | Toegankelijkheid (#67): focus in dialogen, `prefers-reduced-motion` |
| `test_beheer_keycloak_login.py` | Inloggen in de beheeromgeving via het formulier van Keycloak en uitloggen (#251). Alleen met Keycloak aan en `OMNITWIN_TESTACCOUNTS=1` + `KEYCLOAK_ADMIN_PASSWORD` (`--env-file .env`); `OMNITWIN_BASE_URL` moet dan het publieke adres zijn (de host uit `OIDC_ISSUER`), niet `http://traefik` |
| `test_viewer_keycloak_login.py` | Viewer achter Keycloak-login (#266): `/` stuurt door naar het formulier van Keycloak, na inloggen als lezer de kaart met je naam in de kop, en uitloggen. Alleen bij `VIEWER_TOEGANG=inloggen`; lezer = demo-account `gebruiker` (`OMNITWIN_OMGEVING=demo`) of een testaccount. Met de standaard (`open`) overgeslagen |

Uitkomsten:

- **passed**: stap(pen) geautomatiseerd en in orde;
- **xfail** (strict): toetst een functie of data die (nog) ontbreekt, of een bekende bug.
  Slaagt zo'n test onverwacht, dan faalt de run: werk dan testcase en test bij;
- **skipped**: niet te automatiseren (subjectieve reviewstap) of niet aanwezig in de
  sample; de reden staat in de skip-melding (`pytest -rs`).

## Draaien (reproduceerbaar, in de Playwright-container)

De Playwright-versie in `requirements.txt` moet gelijk zijn aan de image-tag.

```bash
# 1. Verse stack met de sample dataset
docker compose down -v && docker compose up -d --build

# 2. Tests in de Playwright-container op het compose-netwerk
docker run --rm --network d-omnitwin_default \
    -v "$PWD":/work -w /work \
    -e OMNITWIN_BASE_URL=http://traefik \
    mcr.microsoft.com/playwright/python:v1.63.0-noble \
    sh -c "pip install -q --root-user-action=ignore -r tests/e2e/requirements.txt \
           && pytest -m e2e tests/e2e -p no:cacheprovider -rs"
```

Het netwerk heet `<projectnaam>_default`; bij `COMPOSE_PROJECT_NAME=e2e62` is dat
`e2e62_default`. Op Windows (Git Bash) `MSYS_NO_PATHCONV=1` voor het commando zetten
en het volume als Windows-pad opgeven.

TC-06-004 stap 1-4 vraagt een LLM (zie `scripts/llm/kies_provider.py`); zonder LLM wordt die
test overgeslagen. Een lokaal model op CPU kan traag zijn: `E2E_LLM_TIMEOUT` (seconden, standaard 300).

Een volledige run duurt ongeveer 5 minuten (WebGL draait in de container via
software-rendering). De browser haalt de kaartbibliotheken van de CDN's en de
basiskaart van PDOK; TC-01-003 B laadt BAG-woonplaatsen via de backend van
`service.pdok.nl`. Zonder internettoegang wordt die test overgeslagen.

## Lokaal draaien (zonder container)

```bash
pip install -r tests/e2e/requirements.txt && playwright install chromium
OMNITWIN_BASE_URL=http://localhost:8000 pytest -m e2e tests/e2e   # E2E_HEADED=1 toont de browser
```

## Bij een fout

Screenshot (volledige pagina) en de opgevangen consolefouten van de mislukte test komen
in `tests/e2e/artifacts/` (niet in git).

## Werkwijze in de tests

- Wachten gebeurt op concrete toestand (`window.state`, `window.kompasViz`, elementen),
  niet op vaste pauzes.
- Kaartklikken zijn echte muisklikken op het deck.gl-canvas: het klikpunt wordt berekend
  met `viewport.project()` (punt-in-polygoon, zo ver mogelijk van de rand van de buurt,
  niet afgedekt volgens `document.elementFromPoint()`) en één keer bevestigd met
  `deck.pickObject()`. Ligt de buurt buiten beeld, dan zoomt de test uit met het scrollwiel.
  Waar de klik zelf niet het onderwerp is, selecteert de test via de `onClick`-handler van
  de gebiedenlaag (zelfde codepad).
- Onder CPU-druk duurt de pick die deck.gl bij `pointerdown` doet langer dan de tapdrempel
  van 250 ms, en dan maakt deck.gl van de muisklik geen klik (#212). De test meet dat per
  klik en verruimt dan voor die pagina de tijdsdrempel van de click-herkenner, met een
  waarschuwing in de pytest-uitvoer; de klik blijft een echte klik.
- Wachttijden schalen met de gemeten traagheid van de renderer: bij het openen van elke
  pagina meet de test een kleine vaste WebGL-taak (`meet_traagheid`, `geschaald()`); na de
  run staat het overzicht onder "Traagheid renderer". Sneller dan in rust wordt niets.
- De tegels van de PDOK-basiskaart worden in de tests leeg beantwoord (HTTP 204): ze kosten
  onder software-WebGL veel rekentijd en geen test gaat erover. Tests die ze nodig hebben
  krijgen de marker `basiskaart`; `E2E_BASISKAART=1` laadt ze altijd.
- Het Kompas wordt bediend met echte klikken op het middelpunt van een segment van het
  zonnediagram.
- Welkomstmodal en tips worden via `localStorage` overgeslagen, behalve in TC-06-001
  (daar hoort de onboarding bij het scenario).
