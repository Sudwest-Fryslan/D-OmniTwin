-- Favorieten en laatste kaartpositie per ingelogde gebruiker (#258); idempotent.
--
-- Sleutel (eigenaar): de `sub` uit de OIDC-sessie (Keycloak), of `lokaal:<users.id>` voor een lokaal
-- account. Geen naam, e-mail of andere profielgegevens. Persoonlijke gegevens, geen inrichting: ze
-- horen niet in de portabiliteitspoort en niet in PostgREST (geen GRANT in R__api_rollen.sql).
--
-- gebruiker_voorkeuren: één rij per gebruiker, met de laatste kaartpositie en wanneer de gebruiker
--   voor het laatst iets met zijn voorkeuren deed. Na 365 dagen zonder gebruik ruimt de dagelijkse
--   opruimtaak de rij op, en via de cascade ook de favorieten (docs/5-secops/privacy-quickscan.md).
-- gebruiker_favorieten: een gebiedenselectie met een naam; naam uniek per gebruiker.

CREATE TABLE IF NOT EXISTS public.gebruiker_voorkeuren (
    eigenaar       text PRIMARY KEY CHECK (length(eigenaar) BETWEEN 1 AND 255),
    kaartpositie   jsonb,                               -- {longitude, latitude, zoom, pitch, bearing}
    laatst_gebruikt timestamptz NOT NULL DEFAULT now(),
    aangemaakt     timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.gebruiker_voorkeuren IS
    'Voorkeuren per ingelogde gebruiker (#258): sleutel = OIDC-sub of lokaal:<users.id>; opgeruimd na 365 dagen zonder gebruik';
CREATE INDEX IF NOT EXISTS idx_gebruiker_voorkeuren_laatst ON public.gebruiker_voorkeuren (laatst_gebruikt);

CREATE TABLE IF NOT EXISTS public.gebruiker_favorieten (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    eigenaar        text NOT NULL REFERENCES public.gebruiker_voorkeuren(eigenaar) ON DELETE CASCADE,
    naam            text NOT NULL CHECK (length(btrim(naam)) BETWEEN 1 AND 80),
    gebiedstype_id  uuid,
    gebied_ids      text[] NOT NULL CHECK (cardinality(gebied_ids) BETWEEN 1 AND 2000),
    aangemaakt      timestamptz NOT NULL DEFAULT now(),
    gewijzigd       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (eigenaar, naam)
);
COMMENT ON TABLE public.gebruiker_favorieten IS
    'Favoriete gebiedenselecties per gebruiker (#258); verdwijnen met gebruiker_voorkeuren';
