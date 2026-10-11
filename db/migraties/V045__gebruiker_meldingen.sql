-- Terugmeldvoorziening voor gebruikers (#311); idempotent.
--
-- Centrale en contextuele meldingen van gebruikers over data, AI-antwoorden, bugs of suggesties.
-- D-OmniTwin fungeert als regielogboek ("bron blijft bron"); fouten in brondata worden gesignaleerd
-- en doorgestuurd naar de respectievelijke bronhouder.
-- Standaard anoniem; optioneel met e-mailadres voor wie terugkoppeling wenst.
-- Niet in PostgREST (geen publicatie naar api-schema); uitsluitend via FastAPI met beheerautorisatie.

CREATE TABLE IF NOT EXISTS public.gebruiker_meldingen (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type            text NOT NULL CHECK (type IN ('data', 'ai', 'systeem', 'overig')),
    onderwerp       text NOT NULL CHECK (length(btrim(onderwerp)) BETWEEN 1 AND 120),
    toelichting     text NOT NULL CHECK (length(btrim(toelichting)) BETWEEN 1 AND 4000),
    context         jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (pg_column_size(context) <= 10240),
    melder_email    text CHECK (melder_email IS NULL OR melder_email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    status          text NOT NULL DEFAULT 'nieuw' CHECK (status IN ('nieuw', 'doorgestuurd_naar_bron', 'in_behandeling', 'afgehandeld', 'afgewezen')),
    notitie_beheer  text,
    aangemaakt_op   timestamptz NOT NULL DEFAULT now(),
    bijgewerkt_op   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.gebruiker_meldingen IS
    'Terugmeldvoorziening voor gebruikers (#311): regielogboek voor feedback op data, AI, techniek of suggesties; beheer via admin-API.';

CREATE INDEX IF NOT EXISTS idx_gebruiker_meldingen_status 
    ON public.gebruiker_meldingen (status, aangemaakt_op DESC);
