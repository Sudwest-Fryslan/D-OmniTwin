-- Gebiedstypen voor de CBS- en SWF-gebiedsindelingen via de laad-API (#205). Idempotent.
-- Gelijk aan db/stuurdata/stuurdata_seed.sql, voor bestaande installaties.
--
-- 1. 'CBS wijken' (0fdd1ab2, de UUID uit de SWF-monitor): nodig voor dataset cbs-gebied-wijken
--    (use case cbs-gebiedsindelingen), ook zonder de SWF-definities.
-- 2. Aanname A5 (#222, pre-release): UUID d210c084 is 'CBS buurten bebouwde komgrens' zoals in
--    de SWF-monitor, niet 'Custom Gebied Type'. Alleen bijgewerkt als hij nog de oude naam heeft.

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau)
SELECT '0fdd1ab2-0963-471d-a47a-d7e080461a30', 'CBS wijken', 'CBS_WIJK',
       'Wijkindelingen volgens het Centraal Bureau voor de Statistiek', 'CBS', 'Wijk'
WHERE NOT EXISTS (SELECT 1 FROM public.gebiedstypes WHERE code = 'CBS_WIJK')
ON CONFLICT (id) DO NOTHING;

UPDATE public.gebiedstypes
SET naam = 'CBS buurten bebouwde komgrens',
    code = 'CBS_BUURT_BBK',
    beschrijving = 'CBS-buurten gesplitst in een deel binnen en buiten de bebouwde kom (SWF-monitor; aanname A5, #222)',
    niveau = 'Buurtdeel bebouwde kom'
WHERE id = 'd210c084-506b-48b4-87c9-b7d4bf422553'
  AND code = 'CUSTOM'
  AND NOT EXISTS (SELECT 1 FROM public.gebiedstypes WHERE code = 'CBS_BUURT_BBK');
