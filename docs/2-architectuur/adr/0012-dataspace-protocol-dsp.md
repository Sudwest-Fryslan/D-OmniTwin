# 0012. Dataspace-protocol: DSP (DCAT/ODRL) over HTTPS, geen iSHARE

- Status: aanvaard
- Datum: 2026-10-12
- Issue: https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/32
- Raakt: ADR 0007 (mesh van instanties), https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/33 (transport/trust), epic provider https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/380

## Context

D-OmniTwin moet data en inrichting aanbieden aan andere instanties en aan FRLDS/DataFryslân (ADR 0007). Daarvoor is een protocol nodig voor de catalogus en de afspraken (contract). Opties in RFC #32: iSHARE, het Eclipse Dataspace Protocol (DSP) en FSC als transport.

## Besluit

1. **DSP is de standaard** voor de catalogus (DCAT) en de contractonderhandeling (ODRL).
2. **Geen iSHARE.** iSHARE regelt identiteit, geen catalogus of contract, en FRLDS/DataFryslân dwingt het niet af. Geen onnodige afhankelijkheid.
3. **Lichtgewicht start (provider worden):** eerst de DCAT/DSP-catalogus aanbieden over gewoon HTTPS.
4. **Transport en trust pas bij concrete behoefte:** FSC (of een andere adapter) pas als een tegenpartij of de gevoeligheid van de data erom vraagt (#33).

## Alternatieven

- **iSHARE:** lost alleen identiteit op; catalogus en contract blijven open. Afgevallen.
- **Direct FSC:** zwaar voor open data en inrichting; blijft optie per afspraak.

## Gevolgen

- Mijlpaal 0.10.0 (provider, #380) bouwt op DSP over HTTPS; de test-dataspace gebruikt twee eigen instanties en de EDC Minimum Viable Dataspace.
- Identiteit per instantie: OIN, later PKIoverheid; niet iSHARE (ADR 0007 punt 2 noemt iSHARE nog als mogelijkheid; dat vervalt hiermee).
