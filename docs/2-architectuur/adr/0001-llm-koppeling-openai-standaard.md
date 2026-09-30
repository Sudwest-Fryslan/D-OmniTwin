# 0001. LLM-koppeling via de OpenAI Chat Completions-standaard, naast Ollama

- Status: voorgesteld
- Datum: 2026-09-30
- Issue: #88

## Context

De backend spreekt alleen Ollama's eigen API (`/api/generate`). Daarmee zitten we vast aan één runtime. De de-facto standaard voor LLM-koppelingen is de OpenAI Chat Completions-API (`/v1/chat/completions`). Die spreken Ollama (via `/v1`), vLLM, LM Studio, Azure OpenAI, de meeste aanbieders en gateways zoals LiteLLM.

Het project wil leveranciersonafhankelijk blijven en ruimte houden voor federatieve of regionale modellen (FRLLLM, #20/#23). Tegelijk is een lokaal model (Ollama + Qwen) de standaard en mogen bestaande installaties niet veranderen.

## Besluit

- `llm_config` krijgt een kolom `api_type`: `ollama` (standaard, huidig gedrag) of `openai` (Chat Completions).
- `services/llm_service.py` ondersteunt beide paden. Het Ollama-pad blijft gelijk, op het uitzetten van de denk-modus na (hieronder).
- Een API-sleutel staat nooit in de database (die is anoniem leesbaar, #57) maar in `.env` als `LLM_API_KEY`, en wordt alleen bij `openai` meegestuurd.
- De denk-modus van redeneermodellen (Qwen3, DeepSeek-R1) staat bewust standaard uit (`LLM_THINK=false`). De teksten zijn kort (chat ≤ 80 woorden) en hebben geen redeneerstap nodig, terwijl denken duizenden tokens kost: met qwen3:4b op ~9 tokens/s duurde een chatantwoord meer dan vijf minuten. Ollama-pad: `"think": false`. OpenAI-pad (`think` is daar geen standaardveld): `reasoning_effort: "none"` (Ollama `/v1`; weg te laten met `LLM_REASONING_EFFORT=` voor servers die het niet kennen) en voor Qwen3-modellen `/no_think` achter de systeemprompt. `<think>…</think>` wordt altijd uit het antwoord gehaald.
- Optioneel draait een LiteLLM-gateway in de compose (profiel `llm-gateway`). Die stuurt standaard door naar het lokale Ollama en biedt ruimte voor fallbacks, centrale sleutels en logging. Zonder gateway werkt alles zoals nu.

## Alternatieven

- **Alleen Ollama-native houden.** Geen werk, maar blijft vastzitten aan één runtime; vLLM, aanbieders en gateways zijn niet bruikbaar.
- **LiteLLM verplicht maken.** Eén koppelpunt, maar een extra container en afhankelijkheid voor elke installatie, ook als die alleen lokaal Ollama gebruikt.
- **Een SDK per aanbieder** (openai, anthropic, ...). Meer code en dependencies per aanbieder, terwijl vrijwel iedereen de Chat Completions-API al spreekt.

## Gevolgen

- Bestaande installaties blijven werken: zonder migratie of met `api_type=ollama` blijft de koppeling gelijk. Wel antwoorden redeneermodellen voortaan zonder denkstap, dus sneller.
- Elke OpenAI-compatibele server of gateway is te koppelen door alleen `llm_config` en eventueel `LLM_API_KEY` aan te passen.
- Modelspecifieke opties (denk-modus, contextlengte) zijn in het OpenAI-pad niet gestandaardiseerd; `reasoning_effort` en `/no_think` zijn een beste poging. Een server die `reasoning_effort` weigert, zet je met `LLM_REASONING_EFFORT=` (leeg).
- Wie de denk-modus wel wil (bv. voor zwaardere analyses), zet `LLM_THINK=true`; dan beslist het model zelf, zoals vóór dit besluit.
- Twee paden betekent twee testpaden: unit-tests met een nep-LLM in de CI, en tests met een echt model (marker `llm`) handmatig.
