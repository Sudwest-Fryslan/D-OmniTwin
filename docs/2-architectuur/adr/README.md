# Architectuurbesluiten (ADR's)

Een ADR (Architecture Decision Record) legt één architectuurbesluit vast: waarom we iets zo doen, welke alternatieven er waren en wat de gevolgen zijn. Zo blijft de redenering terug te vinden, ook als de mensen die het besloten er niet meer bij zijn.

## Werkwijze

- Eén bestand per besluit: `NNNN-korte-titel.md`, doorlopend genummerd.
- Een ADR wordt niet herschreven als het besluit verandert. Schrijf dan een nieuwe ADR en zet de oude op status "vervangen door NNNN".
- Status: `voorgesteld` → `aanvaard` (of `afgewezen`) → eventueel `vervangen door NNNN`.
- Een ADR hoort bij een issue en wordt via een PR voorgesteld; de review is de discussie.

## Sjabloon

```markdown
# NNNN. Titel van het besluit

- Status: voorgesteld
- Datum: JJJJ-MM-DD
- Issue: #NN

## Context
Welk probleem, welke krachten spelen er?

## Besluit
Wat we doen.

## Alternatieven
Wat we overwogen en waarom niet.

## Gevolgen
Wat wordt makkelijker, wat moeilijker, wat moet er nog gebeuren.
```

## Index

| Nr | Titel | Status |
|----|-------|--------|
| [0001](0001-llm-koppeling-openai-standaard.md) | LLM-koppeling via de OpenAI Chat Completions-standaard, naast Ollama | voorgesteld |
| [0004](0004-een-ingang-voor-vullen.md) | D-OmniTwin vullen via één laad-API: dataset-registratie en leveringen | voorgesteld |
| [0005](0005-gescheiden-apis-per-doel.md) | Gescheiden API's per doel volgens de NL GOV API Design Rules | voorgesteld |
| [0006](0006-usecase-als-declaratieve-app.md) | Use case als declaratieve app met eigen specificatie | voorgesteld |
| [0007](0007-geen-multi-tenancy-mesh-van-instanties.md) | Geen multi-tenancy: autonome D-OmniTwin-instanties in een mesh | voorgesteld |
| [0008](0008-inloggen-beheer-via-keycloak-bff.md) | Inloggen in de beheeromgeving via Keycloak, met de backend als BFF | voorgesteld |
| [0009](0009-viewer-achter-login-forwardauth.md) | Viewer optioneel achter Keycloak-login, data-API's via Traefik forwardAuth | voorgesteld |
| [0010](0010-toegang-per-laag-en-bron.md) | Toegang per laag en bron: openbaar of intern, afgedwongen in de database en de forwardAuth | voorgesteld |
