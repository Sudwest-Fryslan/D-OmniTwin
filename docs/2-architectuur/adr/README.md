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
| [0002](0002-databronnen-als-dataproduct.md) | Databronnen als dataproduct: ontsluiten met contract, metadata, semantiek en voorwaarden | voorgesteld |
| [0003](0003-use-cases-als-eenheid.md) | Use cases als eenheid van functionaliteit, test en demodata | voorgesteld |
