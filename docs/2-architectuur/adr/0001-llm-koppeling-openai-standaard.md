# 0001. LLM-koppeling via de OpenAI Chat Completions-standaard, naast Ollama

- Status: voorgesteld
- Datum: 2026-09-30
- Issue: #88

## Context

De backend spreekt alleen Ollama's eigen API (`/api/generate`). Daarmee zitten we vast aan één runtime. De de-facto standaard voor LLM-koppelingen is de OpenAI Chat Completions-API (`/v1/chat/completions`). Die spreken Ollama (via `/v1`), vLLM, LM Studio, Azure OpenAI, de meeste aanbieders en gateways zoals LiteLLM.

Het project wil leveranciersonafhankelijk blijven en ruimte houden voor federatieve of regionale modellen (FRLLLM, #20/#23). Tegelijk is een lokaal model (Ollama + Qwen) de standaard en mogen bestaande installaties niet veranderen.

## Besluit

- `llm_config` krijgt een kolom `api_type`: `ollama` (standaard, huidig gedrag) of `openai` (Chat Completions).
- `services/llm_service.py` ondersteunt beide paden. Het Ollama-pad blijft ongewijzigd.
- Een API-sleutel staat nooit in de database (die is anoniem leesbaar, #57) maar in `.env` als `LLM_API_KEY`, en wordt alleen bij `openai` meegestuurd.
- Optioneel draait een LiteLLM-gateway in de compose (profiel `llm-gateway`). Die stuurt standaard door naar het lokale Ollama en biedt ruimte voor fallbacks, centrale sleutels en logging. Zonder gateway werkt alles zoals nu.

## Alternatieven

- **Alleen Ollama-native houden.** Geen werk, maar blijft vastzitten aan één runtime; vLLM, aanbieders en gateways zijn niet bruikbaar.
- **LiteLLM verplicht maken.** Eén koppelpunt, maar een extra container en afhankelijkheid voor elke installatie, ook als die alleen lokaal Ollama gebruikt.
- **Een SDK per aanbieder** (openai, anthropic, ...). Meer code en dependencies per aanbieder, terwijl vrijwel iedereen de Chat Completions-API al spreekt.

## Gevolgen

- Bestaande installaties merken niets: zonder migratie of met `api_type=ollama` blijft het gedrag gelijk.
- Elke OpenAI-compatibele server of gateway is te koppelen door alleen `llm_config` en eventueel `LLM_API_KEY` aan te passen.
- Modelspecifieke opties (Qwen3 denk-modus, contextlengte) lopen via Ollama-opties; in het OpenAI-pad zijn ze niet gestandaardiseerd. Denk-output (`<think>…</think>`) wordt daar uit het antwoord gefilterd.
- Twee paden betekent twee testpaden: unit-tests met een nep-LLM in de CI, en tests met een echt model (marker `llm`) handmatig.
