CREATE OR REPLACE FUNCTION public.get_indicatoren_stats(p_gebiedstype_id uuid DEFAULT NULL)
RETURNS TABLE (
    uuid uuid,
    naam character varying,
    code character varying,
    omschrijving text,
    eenheid character varying,
    categorie character varying,
    aantal_gebieden_met_data bigint,
    aantal_metingen bigint,
    nieuwste_jaar integer
) AS $$
BEGIN
    IF p_gebiedstype_id IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            COALESCE(COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END), 0)::bigint as aantal_gebieden_met_data,
            COALESCE(COUNT(DISTINCT gd.id), 0)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        LEFT JOIN public.gebieden g ON gd.gebied_id = g.id
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY 
            COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END) DESC NULLS LAST,
            i.naam;
    ELSE
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            0::bigint as aantal_gebieden_met_data,
            COUNT(DISTINCT gd.id)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY i.naam;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
