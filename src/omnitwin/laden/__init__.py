"""Laad-API (/api/laden/v1, #205, #228): registraties, leveringen en de laadstraat.

- `registratie`, `levering`: lokale validatie (ook gebruikt door `python -m omnitwin.usecases controleer`);
- `lezen`, `tabelschema`, `p_waarnemingen`, `p_definities`, `p_geo`, `adapter_swf`: valideren per profiel;
- `laadstraat`, `db`, `opslag`, `verwerker`: ontvangen, staging, publiceren, versies, bewaartermijn;
- `catalogus`, `profielen`, `problemen`: weergaven en Problem Details voor de router (`omnitwin.routers.laden`).
"""
