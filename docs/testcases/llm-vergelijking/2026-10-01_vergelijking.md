# LLM-providervergelijking — 2026-10-01

Gegenereerd door `scripts/llm/vergelijk_providers.py` (#88). Eén run per scenario per aanbieder; LLM-uitvoer varieert per run, dus dit is een momentopname en geen benchmark.

- App: `http://localhost:8106` · sample dataset
- Aanbieders:
  - `ollama`: beschikbaar — via gateway, alias d-omnitwin-ollama · model: `qwen3:4b-instruct`
  - `direct-ollama`: beschikbaar — direct naar Ollama · model: `qwen3:4b-instruct`
  - `claude`: overgeslagen — geen key (ANTHROPIC_API_KEY leeg of afwezig in .env) · model: `anthropic/claude-haiku-4-5`
  - `openai`: overgeslagen — geen key (OPENAI_API_KEY leeg of afwezig in .env) · model: `openai/gpt-4o-mini`
  - `gemini`: beschikbaar — via gateway, alias d-omnitwin-gemini · model: `gemini/gemini-3.8-flash`
- Oorspronkelijke configuratie teruggezet: ja

Legenda: latency · modus (`intelligent_dispatcher` = LLM gaf geldige JSON; `legacy_fallback` = terugval op regels; `vast scenario` = trefwoord uit `chat_scenarios`, geen LLM; `LLM` = rapporttekst door het model; `LLM-fout` = de aanbieder gaf een fout, de tekst is een foutmelding) · woorden (chat: antwoord; rapport: samenvatting) · Nederlands (≥ 3 Nederlandse functiewoorden) · grounding (getallen die niet in de brondata staan, tests/grounding.py; alleen over echte modeltekst).

## Overzicht

| Scenario | `ollama` | `direct-ollama` | `claude` | `openai` | `gemini` |
|---|---|---|---|---|---|
| Chat: 'Hoe groen is Bolsward-Zuidoost?' (BU19000002) | 5.6 s · intelligent_dispatcher · 6 w · NL ja · grounding ok | 6.1 s · intelligent_dispatcher · 6 w · NL ja · grounding ok | overgeslagen (geen key) | overgeslagen (geen key) | 6.4 s · intelligent_dispatcher · 18 w · NL ja · grounding ok |
| Chat: 'Wat valt op in Workum?' (BU19000200) | 0.0 s · vast scenario (geen LLM) | 0.0 s · vast scenario (geen LLM) | overgeslagen (geen key) | overgeslagen (geen key) | 0.0 s · vast scenario (geen LLM) |
| Rapport-narrative BU19000002 (Bolsward-Zuidoost) | 46.4 s · LLM · 99 w · NL ja · grounding ok | 50.3 s · LLM · 92 w · NL ja · grounding ok | overgeslagen (geen key) | overgeslagen (geen key) | 56.7 s · LLM-fout in 1/4 teksten (HTTP 503) · 136 w · NL ja · grounding ok |
| Rapport-narrative BU19000200 (Workum) | 64.1 s · LLM · 104 w · NL ja · grounding ok | 68.0 s · LLM · 92 w · NL ja · grounding ok | overgeslagen (geen key) | overgeslagen (geen key) | 27.2 s · LLM-fout in 5/5 teksten (HTTP 429 rate limit) |

## Chat: 'Hoe groen is Bolsward-Zuidoost?' (BU19000002)

- **`ollama`** (5.6 s, intelligent_dispatcher, d-omnitwin-ollama)
  - acties: TOON_OP_KAART: 🗺 Toon: Bolsward-Zuidoost [BU19000002]
  - > Ik toon de groenindicator voor Bolsward-Zuidoost.
- **`direct-ollama`** (6.1 s, intelligent_dispatcher, qwen3:4b-instruct)
  - acties: TOON_OP_KAART: 🗺 Toon: Bolsward-Zuidoost [BU19000002]
  - > Ik toon de groenindicator voor Bolsward-Zuidoost.
- **`claude`**: overgeslagen (geen key)
- **`openai`**: overgeslagen (geen key)
- **`gemini`** (6.4 s, intelligent_dispatcher, d-omnitwin-gemini)
  - acties: SELECTEER_GEMEENTE: 📍 Gemeente: Súdwest-Fryslân; SELECTEER_GEBIEDSTYPE: 🏙 Toon: Buurten
  - > Bolsward-Zuidoost ligt in de gemeente Súdwest-Fryslân. Ik selecteer de gemeente en de buurtenlaag om het groen te bekijken.

## Chat: 'Wat valt op in Workum?' (BU19000200)

- **`ollama`** (0.0 s, vast scenario (geen LLM))
  - acties: SELECTEER_GEBIEDSTYPE: 🗺️ Toon: Buurten; SELECTEER_GEMEENTE: 📍 Gemeente: Súdwest-Fryslân; OPEN_KOMPAS: 🧭 Open het D-Omni Kompas
  - > Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?
- **`direct-ollama`** (0.0 s, vast scenario (geen LLM))
  - acties: SELECTEER_GEBIEDSTYPE: 🗺️ Toon: Buurten; SELECTEER_GEMEENTE: 📍 Gemeente: Súdwest-Fryslân; OPEN_KOMPAS: 🧭 Open het D-Omni Kompas
  - > Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?
- **`claude`**: overgeslagen (geen key)
- **`openai`**: overgeslagen (geen key)
- **`gemini`** (0.0 s, vast scenario (geen LLM))
  - acties: SELECTEER_GEBIEDSTYPE: 🗺️ Toon: Buurten; SELECTEER_GEMEENTE: 📍 Gemeente: Súdwest-Fryslân; OPEN_KOMPAS: 🧭 Open het D-Omni Kompas
  - > Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?

## Rapport-narrative BU19000002 (Bolsward-Zuidoost)

- **`ollama`** (46.4 s, LLM, d-omnitwin-ollama)
  - 3 domeinsamenvattingen, 438 woorden totaal
  - > Bolsward-Zuidoost toont een positieve kwaliteit van leven met sterke burgerdeelname en goede gezondheidsvoorwaarden, maar wordt gecompenseerd door een zwakke sociale samenhang, weinig vrijwilligerswerk en een hoog aantal…
- **`direct-ollama`** (50.3 s, LLM, qwen3:4b-instruct)
  - 3 domeinsamenvattingen, 422 woorden totaal
  - > Bolsward-Zuidoost toont een positieve kwaliteit van leven met sterke burgerdeelname, uitstekende onderwijsresultaten en goede gezondheid, wat een solide sociale basis vormt. Echter, er zijn duidelijke zwakke punten: een…
- **`claude`**: overgeslagen (geen key)
- **`openai`**: overgeslagen (geen key)
- **`gemini`** (56.7 s, LLM-fout in 1/4 teksten (HTTP 503), d-omnitwin-gemini)
  - 3 domeinsamenvattingen, 423 woorden totaal
  - > Bolsward-Zuidoost toont een stapeling van kwetsbaarheden waarbij fysieke veroudering en sociale erosie elkaar negatief beïnvloeden. De fysieke leefomgeving blijft achter door een verouderde woningvoorraad met lage energi…

## Rapport-narrative BU19000200 (Workum)

- **`ollama`** (64.1 s, LLM, d-omnitwin-ollama)
  - 4 domeinsamenvattingen, 585 woorden totaal
  - > Workum toont een duidelijke kwetsbaarheid op meerdere fronten: de sociale veiligheid is verzwakt door hoge inbreuken en schade in open ruimte, terwijl de fysieke leefomgeving tekortvalt in energie-efficiëntie en comfort.…
- **`direct-ollama`** (68.0 s, LLM, qwen3:4b-instruct)
  - 4 domeinsamenvattingen, 571 woorden totaal
  - > Workum toont een wijk met een sterke bevolkingsbasis en actieve inwoners, maar wordt gecombineerd door een duidelijke onveilige sfeer, een ouderenoverweldiging en een slechte energie-efficiëntie. De verhoogde inbreuken e…
- **`claude`**: overgeslagen (geen key)
- **`openai`**: overgeslagen (geen key)
- **`gemini`** (27.2 s, LLM-fout in 5/5 teksten (HTTP 429 rate limit), d-omnitwin-gemini)
  - 4 domeinsamenvattingen, 0 woorden totaal
  - > LLM-server op http://llm-gateway:4000 gaf een fout (429)

## Toelichting (handmatig)

- **Workum-chat test geen LLM.** "Wat valt op in Workum?" bevat het trefwoord `workum` van het scenario Beleidsadviseur (`chat_scenarios.trigger_keywords`) en krijgt daarom bij elke aanbieder de vaste scenariotekst. Wil je hier het model toetsen, kies dan een vraag zonder trefwoord of haal `workum`/`makkum` uit de trefwoorden.
- **Kaartactie in de groen-chat.** Ollama (`qwen3:4b-instruct`) geeft `Toon: Bolsward-Zuidoost` met de buurtcode als `indicator_uuid`; de knop kan zo geen indicator tonen. De zoekstap vindt in de sample geen indicatoren (`indicatoren: []`), dus het model heeft geen uuid om uit te kiezen. Gemini kiest gemeente + buurtenlaag in plaats van een kaartactie.
- **Gemini gratis tier.** Limieten voor `gemini-3.8-flash`: 5 verzoeken per minuut en 20 per dag per model. Eén rapport-narrative kost 4-6 modelaanroepen. Het Bolsward-rapport lukte (één domeintekst gaf 503: Google overbelast), bij het Workum-rapport was de daglimiet op (429). Een eerdere run die dag (zonder pauzes) liep al op de minuutlimiet; vandaar de standaardpauze van 65 s tussen scenario's bij externe aanbieders. `gemini-2.5-flash` is voor nieuwe sleutels niet meer beschikbaar (404).
- **Latency.** Lokaal op CPU, met `qwen3:4b-instruct`; via de gateway of direct maakt nauwelijks verschil.
