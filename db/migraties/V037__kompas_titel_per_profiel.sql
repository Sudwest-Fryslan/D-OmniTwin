-- Kompas: een kwadrantnaam is uniek per profiel, niet over alle profielen (#222).
--
-- kompas_titels had naast unique_titel_per_config (config_id, naam) ook een unieke naam over alle
-- Kompasprofielen. Daardoor kon een tweede profiel geen kwadrant met dezelfde naam hebben (bijv.
-- 'Klimaat' in het Klimaat Kompas en in SWF Klimaat, of de kwadranten van het Volledig Kompas in
-- SWF Basis). De unieke naam per profiel blijft. Idempotent.
ALTER TABLE public.kompas_titels DROP CONSTRAINT IF EXISTS kompas_titels_naam_key;
