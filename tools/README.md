# tools/

Hulpmiddelen voor beheerders en ontwikkelaars. Geen onderdeel van de app, de installatie of de CI.

| Script | Wat het doet | Status |
|---|---|---|
| `validate_gebiedsmonitor.py` | Rapport over de kwaliteit van de gebiedsmonitor-data | ⚠️ leest nog `config.ini` (bestaat niet meer); ombouwen naar `.env`/`DATABASE_*` |
| `validate_kompas_uuid_mapping.py` | Rapport over de koppeling indicator-UUID ↔ Kompas | ⚠️ idem |

In fase 6 van de herstructurering (#182) komen hier ook `scripts/ai`, `scripts/llm` en `scripts/docs`.
