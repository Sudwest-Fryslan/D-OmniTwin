-- Toegang per laag en bron: openbaar of intern (#254, ADR 0010). Idempotent.
--
-- Bron van de waarheid is de registratie in de laad-API: `dct:accessRights` in de beschrijving
-- (DCAT-AP-NL). PUBLIC = openbaar, al het andere (RESTRICTED, NON_PUBLIC, ontbrekend) = intern.
-- Daaruit volgt de toegang van wat de dataset publiceert:
--   laden.datasets.toegang          afgeleid van dct:accessRights (gegenereerde kolom)
--   public.externe_kaartlagen       de kaartlaag van een dataset met profiel kaartlaag
--   public.indicatoren              intern als een interne dataset de indicator definieert, of als
--                                   al zijn waarden uit interne datasets komen
--   public.gebied_data              intern als de waarde uit een interne dataset komt of de
--                                   indicator intern is
-- Alles wat niet via de laad-API kwam (stuurdata, uploads, PDOK-lagen) blijft openbaar.
--
-- Afdwingen in de database:
--   omnitwin_openbaar  rol waarnaar de backend per anoniem verzoek schakelt (SET ROLE, zie
--                      src/omnitwin/toegang.py). Lid van de eigenaar (zelfde rechten op tabellen),
--                      maar geen superuser, dus row level security geldt.
--   RLS                op indicatoren, gebied_data en externe_kaartlagen: omnitwin_openbaar ziet alleen
--                      `openbaar`; elke andere rol (eigenaar, laden_schrijver) alles. FORCE, omdat een
--                      lid van de eigenaar anders als eigenaar telt. Een superuser (POSTGRES_USER in
--                      Docker, de backend buiten een anoniem verzoek, db-init, back-up) ziet alles.
-- Views in public die deze tabellen lezen krijgen security_invoker (R__api_rollen.sql), zodat RLS
-- ook door de view heen werkt. PostgREST filtert in de views van schema api (R__api_rollen.sql).

-- ── Rol voor anonieme verzoeken van de backend ─────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'omnitwin_openbaar') THEN
        CREATE ROLE omnitwin_openbaar NOLOGIN;
    END IF;
END
$$;
ALTER ROLE omnitwin_openbaar NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT;

-- Lid van de eigenaar (de gebruiker die db-init draait, in Docker POSTGRES_USER): dezelfde rechten op
-- tabellen, reeksen en functies, zonder superuser. Een superuser mag zonder lidmaatschap naar deze rol.
DO $$
BEGIN
    IF NOT pg_has_role('omnitwin_openbaar', current_user, 'MEMBER') THEN
        EXECUTE format('GRANT %I TO omnitwin_openbaar', current_user);
    END IF;
END
$$;

-- ── Kolommen ─────────────────────────────────────────────────────────────────
ALTER TABLE public.indicatoren        ADD COLUMN IF NOT EXISTS toegang text NOT NULL DEFAULT 'openbaar';
ALTER TABLE public.gebied_data        ADD COLUMN IF NOT EXISTS toegang text NOT NULL DEFAULT 'openbaar';
ALTER TABLE public.externe_kaartlagen ADD COLUMN IF NOT EXISTS toegang text NOT NULL DEFAULT 'openbaar';

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['indicatoren', 'gebied_data', 'externe_kaartlagen'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = t || '_toegang_check'
                       AND conrelid = ('public.' || t)::regclass) THEN
            EXECUTE format('ALTER TABLE public.%I ADD CONSTRAINT %I CHECK (toegang IN (''openbaar'', ''intern''))',
                           t, t || '_toegang_check');
        END IF;
    END LOOP;
END
$$;
COMMENT ON COLUMN public.indicatoren.toegang IS
    'openbaar of intern (#254): intern als een interne dataset hem definieert of al zijn waarden levert';
COMMENT ON COLUMN public.gebied_data.toegang IS
    'openbaar of intern (#254): intern als de levering uit een interne dataset komt of de indicator intern is';
COMMENT ON COLUMN public.externe_kaartlagen.toegang IS
    'openbaar of intern (#254): intern alleen zichtbaar met de rol lezer of beheerder';
CREATE INDEX IF NOT EXISTS idx_gebied_data_intern ON public.gebied_data (indicator_uuid) WHERE toegang = 'intern';

-- Toegang van een registratie: uit dct:accessRights (tekst of {"@id": ...})
CREATE OR REPLACE FUNCTION laden.toegang_uit_dcat(beschrijving jsonb)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT CASE WHEN rtrim(coalesce(beschrijving->'dct:accessRights'->>'@id', beschrijving->>'dct:accessRights'), '/')
                     = 'http://publications.europa.eu/resource/authority/access-right/PUBLIC'
                THEN 'openbaar' ELSE 'intern' END
$$;
GRANT EXECUTE ON FUNCTION laden.toegang_uit_dcat(jsonb) TO laden_schrijver;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'laden' AND table_name = 'datasets' AND column_name = 'toegang') THEN
        ALTER TABLE laden.datasets
            ADD COLUMN toegang text GENERATED ALWAYS AS (laden.toegang_uit_dcat(beschrijving)) STORED;
    END IF;
END
$$;
COMMENT ON COLUMN laden.datasets.toegang IS 'openbaar (dct:accessRights PUBLIC) of intern (#254); afgeleid, niet zelf zetten';

-- ── Doorrekenen: van dataset naar indicator, waarde en kaartlaag ────────────
-- SECURITY DEFINER: draait met de rechten van de eigenaar (geen RLS), ook als de laadstraat
-- (laden_schrijver) hem aanroept.
CREATE OR REPLACE FUNCTION public.herbereken_toegang(p_indicatoren uuid[])
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    n integer;
BEGIN
    UPDATE public.indicatoren i SET toegang = x.toegang
    FROM (SELECT j.uuid, CASE
              WHEN EXISTS (SELECT 1 FROM laden.dataset_objecten o JOIN laden.datasets d ON d.id = o.dataset_id
                           WHERE o.soort = 'indicator' AND o.sleutel = j.uuid::text AND d.toegang = 'intern')
                OR (EXISTS (SELECT 1 FROM public.gebied_data gd
                            JOIN laden.leveringen l ON l.id = gd.levering_id
                            JOIN laden.datasets d ON d.id = l.dataset_id
                            WHERE gd.indicator_uuid = j.uuid AND d.toegang = 'intern')
                    AND NOT EXISTS (SELECT 1 FROM public.gebied_data gd
                                    LEFT JOIN laden.leveringen l ON l.id = gd.levering_id
                                    LEFT JOIN laden.datasets d ON d.id = l.dataset_id
                                    WHERE gd.indicator_uuid = j.uuid AND coalesce(d.toegang, 'openbaar') = 'openbaar'))
              THEN 'intern' ELSE 'openbaar' END AS toegang
          FROM public.indicatoren j WHERE j.uuid = ANY(p_indicatoren)) x
    WHERE i.uuid = x.uuid AND i.toegang <> x.toegang;

    UPDATE public.gebied_data gd SET toegang = x.toegang
    FROM (SELECT g.id, CASE WHEN i.toegang = 'intern' OR d.toegang = 'intern' THEN 'intern' ELSE 'openbaar' END AS toegang
          FROM public.gebied_data g
          JOIN public.indicatoren i ON i.uuid = g.indicator_uuid
          LEFT JOIN laden.leveringen l ON l.id = g.levering_id
          LEFT JOIN laden.datasets d ON d.id = l.dataset_id
          WHERE g.indicator_uuid = ANY(p_indicatoren)) x
    WHERE gd.id = x.id AND gd.toegang IS DISTINCT FROM x.toegang;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$$;
COMMENT ON FUNCTION public.herbereken_toegang(uuid[]) IS
    'Toegang van indicatoren en hun waarden opnieuw afleiden uit de datasets (#254)';

CREATE OR REPLACE FUNCTION public.herbereken_toegang_dataset(p_dataset text)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    UPDATE public.externe_kaartlagen k SET toegang = d.toegang
    FROM laden.datasets d
    WHERE d.id = p_dataset AND d.profiel = 'kaartlaag' AND k.id = d.kaartlaag_id AND k.toegang <> d.toegang;
    RETURN public.herbereken_toegang(ARRAY(
        SELECT o.sleutel::uuid FROM laden.dataset_objecten o WHERE o.dataset_id = p_dataset AND o.soort = 'indicator'
        UNION
        SELECT DISTINCT w.indicator_uuid FROM laden.waarnemingen w WHERE w.dataset_id = p_dataset));
END
$$;
COMMENT ON FUNCTION public.herbereken_toegang_dataset(text) IS
    'Toegang van alles wat een dataset publiceerde opnieuw afleiden (#254); na publicatie of gewijzigde registratie';

REVOKE ALL ON FUNCTION public.herbereken_toegang(uuid[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.herbereken_toegang_dataset(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.herbereken_toegang(uuid[]) TO laden_schrijver;
GRANT EXECUTE ON FUNCTION public.herbereken_toegang_dataset(text) TO laden_schrijver;

-- Opzoeken zonder RLS, voor 401/403 in plaats van 404 bij een directe aanroep (backend)
CREATE OR REPLACE FUNCTION public.toegang_indicator(p_uuid uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
AS $$ SELECT toegang FROM public.indicatoren WHERE uuid = p_uuid $$;
CREATE OR REPLACE FUNCTION public.toegang_kaartlaag(p_id integer)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
AS $$ SELECT toegang FROM public.externe_kaartlagen WHERE id = p_id $$;

-- ── Bestaande data ───────────────────────────────────────────────────────────
-- Een kaartlaag uit de laad-API stond tot nu toe uit (actief = false) als hij niet PUBLIC was.
-- Nu bepaalt toegang wie hem ziet; de laag gaat aan als intern.
UPDATE public.externe_kaartlagen k SET toegang = 'intern', actief = true
FROM laden.datasets d
WHERE d.profiel = 'kaartlaag' AND d.kaartlaag_id = k.id AND d.toegang = 'intern';
SELECT public.herbereken_toegang(ARRAY(
    SELECT o.sleutel::uuid FROM laden.dataset_objecten o WHERE o.soort = 'indicator'
    UNION
    SELECT DISTINCT w.indicator_uuid FROM laden.waarnemingen w));

-- ── Row level security ───────────────────────────────────────────────────────
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['indicatoren', 'gebied_data', 'externe_kaartlagen'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS toegang ON public.%I', t);
        EXECUTE format($p$CREATE POLICY toegang ON public.%I
                          USING (toegang = 'openbaar' OR current_user <> 'omnitwin_openbaar')
                          WITH CHECK (true)$p$, t);
    END LOOP;
END
$$;
