-- Meldplek per instantie (#312): waar "Melden" bij een AI-resultaat (en later andere meldingen, #311)
-- naartoe gaat. Leeg = de standaard van D-OmniTwin (nieuw issue in de repository,
-- omnitwin.services.organisatie.STANDAARD_MELD_URL). Idempotent.
ALTER TABLE public.organisatie ADD COLUMN IF NOT EXISTS meld_url text;
COMMENT ON COLUMN public.organisatie.meld_url IS
    'Meldplek (https of mailto) voor meldingen uit de applicatie; leeg = nieuw issue in de repository van D-OmniTwin.';
