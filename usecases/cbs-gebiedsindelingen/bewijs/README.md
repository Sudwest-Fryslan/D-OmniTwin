# Bewijs

Gemaakt door de use-case-uitvoerder: `python -m omnitwin.usecases bewijs <naam>` voert de stappen uit `bewijs.stappen` in `usecase.json` uit tegen een draaiende installatie (Use Case Specificatie, [sectie 12](../../../docs/specificaties/usecase/README.md#12-bewijs); https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/225).

- **In git** (compact): per stap een screenshot `<id>.webp` (1440 × 860, ≤ 150 KB, hooguit 4) en het verslag `bewijs.json`. Alleen bij een release opnieuw gemaakt; dezelfde bestandsnamen worden overschreven, zodat de links in de README's stabiel blijven.
- **Niet in git** (volledig): de originele schermen in `volledig/` en andere uitvoer (zoals `controle.json`). Die gaan als zip bij de GitHub-release (`bewijs --alle --zip bewijs-<versie>.zip`).
