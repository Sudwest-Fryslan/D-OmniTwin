# tools/

Hulpmiddelen voor beheerders en ontwikkelaars. Geen onderdeel van de app of de installatie.

| Script | Wat het doet | Status |
|---|---|---|
| `validate_gebiedsmonitor.py` | Rapport over de kwaliteit van de gebiedsmonitor-data | ⚠️ leest nog `config.ini` (bestaat niet meer); ombouwen naar `.env`/`DATABASE_*` |
| `validate_kompas_uuid_mapping.py` | Rapport over de koppeling indicator-UUID ↔ Kompas | ⚠️ idem |
| `check_links.py` | Controleert de relatieve links (en ankers) in alle `*.md`-bestanden, behalve `docs/archief/`. Draait ook als unittest (`tests/test_docs_links.py`) | ✅ |

In fase 6 van de herstructurering (#182) komen hier ook `scripts/ai`, `scripts/llm` en `scripts/docs`.
