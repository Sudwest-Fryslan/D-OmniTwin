--
-- De eigen organisatie van deze instantie (#231, ADR 0007).
--
-- Eén instantie = één organisatie. Een andere organisatie past dit bestand aan
-- vóór de eerste start (of wijzigt de rij later met SQL; zie
-- docs/9-beheer/installatie.md, "Eigen organisatie").
--
-- docker-entrypoint.sh laadt dit bestand bij elke db-init. Staat er al een rij,
-- dan gebeurt er niets (ON CONFLICT DO NOTHING): een eigen inrichting wordt nooit
-- overschreven.
--
--   gemeente_codes       CBS-gemeentecodes van het eigen gebied; de eerste is de
--                        standaard-referentie in rapporten en de deelgebiedsfunctie
--   benchmark_provincie  standaard-benchmarkgebied (provincienaam zoals in gemeenten.provincie)
--   logos                footer, op volgorde; rol "eigen" of "partner"
--   thema                huisstijl (NLDS-thema): static/css/themes/<thema>.css; standaard d-omnitwin
--
INSERT INTO public.organisatie
    (id, code, naam, korte_naam, oin, gemeente_codes, benchmark_provincie, contact_email, thema, logos)
VALUES (
    true,
    'swf',
    'Gemeente Súdwest-Fryslân',
    'SWF',
    NULL,
    ARRAY['1900'],
    'Fryslân',
    'geo-groep@sudwestfryslan.nl',
    'swf',
    '[
        {"pad": "/static/images/SWF-logo.png", "naam": "Gemeente Súdwest-Fryslân", "rol": "eigen"},
        {"pad": "/static/images/Logo_Tytsjerksteradiel.png", "naam": "Gemeente Tytsjerksteradiel", "rol": "partner"},
        {"pad": "/static/images/LOGO-GEMEENTE-LEEUWARDEN.png", "naam": "Gemeente Leeuwarden", "rol": "partner"},
        {"pad": "/static/images/DF-LOGO-1-1000x1000-TBG.png", "naam": "Datafryslân", "rol": "partner"}
    ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
