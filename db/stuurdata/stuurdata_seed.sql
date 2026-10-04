--
-- D-OmniTwin — Stuurdata Seed (Sample Dataset)
-- Bevat: basisconfiguratie, scenario's, prompts, profielen en instellingen
-- Idempotent: uitgevoerd met INSERT ... ON CONFLICT DO NOTHING
--

-- -------------------------------------------------------------
-- 1. Gebiedstypes
-- -------------------------------------------------------------
INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('afba67cb-6b38-4723-9c95-102a22d5b38a', 'CBS Buurten', 'CBS_BUURT', 'Buurtindelingen volgens het Centraal Bureau voor de Statistiek', 'CBS', 'Buurt', '2026-01-17 00:16:01.343807', '2026-01-17 00:16:01.343807')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('d210c084-506b-48b4-87c9-b7d4bf422553', 'CBS buurten bebouwde komgrens', 'CBS_BUURT_BBK', 'CBS-buurten gesplitst in een deel binnen en buiten de bebouwde kom (SWF-monitor; aanname A5, #222)', 'Gemeente', 'Buurtdeel bebouwde kom', '2026-01-17 00:16:01.343807', '2026-01-17 00:16:01.343807')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('0fdd1ab2-0963-471d-a47a-d7e080461a30', 'CBS wijken', 'CBS_WIJK', 'Wijkindelingen volgens het Centraal Bureau voor de Statistiek', 'CBS', 'Wijk', '2026-10-02 00:00:00', '2026-10-02 00:00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('5871bf75-e014-4e75-8cf0-adf7d61dc196', 'Gemeente', NULL, NULL, NULL, NULL, '2026-02-11 21:19:47.544906', '2026-02-11 21:19:47.544906')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('22401c4c-8272-4895-a0a2-a8d48a0b4c36', 'Provincie', 'PROVINCIE', 'Provincies van Nederland', 'CBS', 'Provincie', '2026-03-17 21:17:51.205183', '2026-03-17 21:17:51.205183')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at)
VALUES ('29fc9f28-89d9-488b-bf68-2ed176187b21', 'Welstandsgebieden', 'WELSTAND', 'Welstandsgebieden zoals gedefinieerd in de welstandsnota', 'Gemeente', 'Gebied', '2026-01-17 00:16:01.343807', '2026-01-17 00:16:01.343807')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 2. Gemeenten (alle 18 Friese gemeenten, CBS-indeling 2024)
--    Codes gelijk aan gemeentecode in init_data/fryslan/buurten_fryslan.geojson,
--    nodig voor seed_fryslan.py (FK gebieden.gemeente_code). De sample zelf
--    gebruikt alleen 1900.
-- -------------------------------------------------------------
INSERT INTO public.gemeenten (code, naam, provincie, is_eiland, created_at, updated_at)
VALUES
    ('0059', 'Achtkarspelen',     'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0060', 'Ameland',           'Fryslân', TRUE,  '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0072', 'Harlingen',         'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0074', 'Heerenveen',        'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0080', 'Leeuwarden',        'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0085', 'Ooststellingwerf',  'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0086', 'Opsterland',        'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0088', 'Schiermonnikoog',   'Fryslân', TRUE,  '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0090', 'Smallingerland',    'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0093', 'Terschelling',      'Fryslân', TRUE,  '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0096', 'Vlieland',          'Fryslân', TRUE,  '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0098', 'Weststellingwerf',  'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('0737', 'Tytsjerksteradiel', 'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('1891', 'Dantumadiel',       'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('1900', 'Súdwest-Fryslân',   'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('1940', 'De Fryske Marren',  'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('1949', 'Waadhoeke',         'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045'),
    ('1970', 'Noardeast-Fryslân', 'Fryslân', FALSE, '2026-02-08 14:31:37.011045', '2026-02-08 14:31:37.011045')
ON CONFLICT (code) DO NOTHING;

-- -------------------------------------------------------------
-- 3. Kompas Configuraties
-- -------------------------------------------------------------
INSERT INTO public.kompas_configuraties (id, naam, beschrijving, is_standaard, is_actief, icoon, versie)
VALUES (1, 'Volledig Kompas', 'Complete overzicht van alle indicatoren over alle thema''s. Geeft een 360° beeld van de leefomgeving.', TRUE, TRUE, '🌍', 1)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.kompas_configuraties (id, naam, beschrijving, is_standaard, is_actief, icoon, versie)
VALUES (2, 'Klimaat Kompas', $$Focus op klimaat, duurzaamheid en fysieke leefomgeving. Indicatoren: groen, klimaatadaptatie, luchtkwaliteit.$$, FALSE, TRUE, '🌡️', 1)
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 4. Kleurenschema's (Color Schemas)
-- -------------------------------------------------------------
INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (1, 'default', 'Standaard rood-geel-groen', '{"max": "#10b981", "mid": "#fbbf24", "min": "#ef4444"}'::jsonb, TRUE, '2026-02-01 17:24:49.996450', '2026-06-17 15:55:14.573306', 'sequential', 'jenks', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (2, 'blue-red', 'Blauw naar rood', '{"max": "#ef4444", "mid": "#a855f7", "min": "#3b82f6"}'::jsonb, TRUE, '2026-02-01 17:24:49.996450', '2026-04-12 15:55:18.549698', 'sequential', 'jenks', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (3, 'green-brown', 'Groen naar bruin (natuur)', '{"max": "#a16207", "mid": "#84cc16", "min": "#10b981"}'::jsonb, TRUE, '2026-02-01 17:24:49.996450', '2026-04-12 14:50:56.866103', 'sequential', 'quantile', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (4, 'monochrome', 'Grijstinten', '{"max": "#e5e7eb", "mid": "#6b7280", "min": "#1f2937"}'::jsonb, TRUE, '2026-02-01 17:24:49.996450', '2026-04-12 14:51:02.124245', 'sequential', 'quantile', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (5, 'sequential-blue', 'Objectief & Feitelijk (bevolking, dichtheid, aantallen)', '{"max": "#08306b", "mid": "#4292c6", "min": "#deebf7"}'::jsonb, TRUE, '2026-02-15 21:20:16.055088', '2026-04-12 14:51:09.174136', 'sequential', 'quantile', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (6, 'colorblind-safe', 'Toegankelijk oordelend (gezondheid, kwaliteit, index)', '{"max": "#0077b6", "mid": "#fdf0d5", "min": "#ae2012"}'::jsonb, TRUE, '2026-02-15 21:20:16.055088', '2026-04-12 14:51:13.966703', 'diverging', 'diverging_midpoint', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (7, 'subjective-gold', 'Divergerend (enquête, beleving)', '{"max": "#f59e0b", "mid": "#f3f4f6", "min": "#7c3aed"}'::jsonb, TRUE, '2026-02-15 21:20:16.055088', '2026-04-12 14:51:18.697853', 'diverging', 'diverging_midpoint', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (8, 'urban-density', 'Intensiteit (bebouwing, verkeer)', '{"max": "#881337", "mid": "#fb7185", "min": "#fff1f2"}'::jsonb, TRUE, '2026-02-15 21:20:16.055088', '2026-04-12 14:51:23.273214', 'sequential', 'jenks', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur)
VALUES (9, 'owner-occupied home', '', '{"max": "#08306b", "mid": "#4292c6", "min": "#deebf7"}'::jsonb, TRUE, '2026-02-17 15:16:11.004416', '2026-02-17 15:16:11.004416', 'sequential', 'equal_interval', 7, '#d1d5db')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 5. Visualisatie Profielen
-- -------------------------------------------------------------
INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (1, 'Bevolking', 'Bevolkingsaantallen en demografische data', '%inwoner%', 5, 'quantile', 7, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:53:30.872717')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (2, 'Dichtheid', 'Dichtheidsmetingen per oppervlakte', '%dichtheid%', 5, 'jenks', 5, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:20:16.075691')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (3, 'Percentage', 'Percentuele indicatoren', '%pct_%', 6, 'quantile', 5, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:20:16.075691')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (4, 'Index Score', 'Index en score waarden', '%index%', 6, 'diverging_midpoint', 5, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:20:16.075691')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (5, 'Bouwjaar', 'Bouwperiode gerelateerde indicatoren', '%bouwjaar%', 5, 'equal_interval', 5, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:20:16.075691')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (6, 'Gezondheid', 'RIVM gezondheidsmonitoring indicatoren', '%gezond%', 6, 'quantile', 5, NULL, TRUE, '2026-02-15 21:20:16.075691', '2026-02-15 21:20:16.075691')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (7, 'profiel_vrijwilliger', 'Vrijwilligerswerk', 'Vrijwilliger%', 7, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (8, 'profiel_koop', 'Koopwoningen', 'Koopwoningen%', 5, 'equal_interval', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (9, 'profiel_mantelzorg', 'Mantelzorg', 'Mantelzorger%', 7, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (10, 'profiel_woningmarkt', 'Woningmarkt breed', '%woning%', 5, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (11, 'profiel_diefstal', 'Diefstal', '%diefstal%', 8, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (12, 'profiel_opleiding', 'Opleidingsniveau', 'Opleidingsniveau%', 5, 'equal_interval', 5, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (13, 'profiel_particulier', 'Particulier huurbezit', 'Particulier%', 5, 'equal_interval', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (14, 'profiel_inwoners', 'Inwonersaantallen', 'Inwoners%', 5, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (15, 'profiel_inkomen', 'Inkomensindicatoren', '%inkomen%', 6, 'diverging_midpoint', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (16, 'profiel_eenzaamheid', 'Eenzaamheid', 'Eenzaam%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (17, 'profiel_eigendom', 'Woningeigendom corporatie', 'Woningcorporatie%', 5, 'equal_interval', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (18, 'profiel_woz', 'WOZ-waarden', '%WOZ%', 5, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (19, 'profiel_standaard', 'Standaard catch-all', '%', 1, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (20, 'profiel_groen', 'Groene leefomgeving', '%groen%', 3, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (21, 'profiel_woningvoorraat', 'Woningvoorraad', 'Woningvoorraad%', 5, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (22, 'profiel_dichtheid', 'Bevolkingsdichtheid', 'Bevolkingsdichtheid%', 5, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (23, 'profiel_grondwater', 'Grondwater', '%grondwater%', 3, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (24, 'profiel_laag_inkomen', 'Laag inkomen huishoudens', 'Huishoudens met laag%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (25, 'profiel_ervaren_gez', 'Ervaren gezondheid', 'Ervaren%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (26, 'profiel_rondkomen', 'Moeite met rondkomen', 'Moeite met%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (27, 'profiel_gevoelstemp', 'Gevoelstemperatuur', 'Gevoelstemperatuur%', 8, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (28, 'profiel_afstand', 'Afstand tot voorzieningen', 'Afstand tot%', 1, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (29, 'profiel_inbraak', 'Inbraak diefstal', '%inbraak%', 8, 'jenks', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (30, 'profiel_bijstand', 'Participatiewet bijstand', 'Participatiewet%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (31, 'profiel_leeftijd', 'Leeftijdsgroepen', '%-% jaar', 5, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (32, 'profiel_overgewicht', 'Overgewicht', 'Overgewicht%', 8, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at)
VALUES (33, 'profiel_minima', 'Minima armoedindicatoren', 'Minima%', 6, 'quantile', 7, NULL, TRUE, '2026-04-22 23:59:30.284282', '2026-04-22 23:59:30.284282')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 6. Chat Scenario's
-- -------------------------------------------------------------
INSERT INTO public.chat_scenarios (id, rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, is_actief, volgorde)
VALUES (1, 'beleidsadviseur', 'Beleidsadviseur', 'Beleid & RO voor gemeenten', $$Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?$$, '[{"type": "SELECTEER_GEBIEDSTYPE", "label": "🗺️ Toon: Buurten", "gebiedstype_id": "buurt"}, {"type": "SELECTEER_GEMEENTE", "label": "📍 Gemeente: Súdwest-Fryslân", "gemeente_code": "1900"}, {"type": "OPEN_KOMPAS", "label": "🧭 Open het D-Omni Kompas"}]'::jsonb, '["beleidsadviseur", "ijsselmeerkust", "makkum", "workum"]'::jsonb, TRUE, 10)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.chat_scenarios (id, rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, is_actief, volgorde)
VALUES (2, 'wijkcontactfunctionaris', 'Dorp/Wijk contactfunctionaris', 'Lokale initiatieven en wijkzaken', $$Je hebt gekozen voor het perspectief van Dorp/Wijk contactfunctionaris. (Dit scenario wordt binnenkort verder ingevuld, je kunt de applicatie ondertussen vrij gebruiken).$$, '[]'::jsonb, '["wijkcontactfunctionaris", "dorpsbelang", "wijkagent"]'::jsonb, TRUE, 20)
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 7. LLM Configuratie
-- -------------------------------------------------------------
INSERT INTO public.llm_config (id, api_url, model_name, aangemaakt_op, bijgewerkt_op)
VALUES (1, 'http://host.docker.internal:11434', 'qwen3:30b', '2026-02-21 11:10:29.863903+00:00', '2026-02-21 11:10:29.863903+00:00')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 8. Log Configuratie
-- -------------------------------------------------------------
INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('ADMIN', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('API', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('AUTH', 'WARNING', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('DATABASE', 'WARNING', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('KAART', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('KOMPAS', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('LLM_CHAT', 'WARNING', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('RAPPORT', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

INSERT INTO public.log_config (category, level, enabled, updated_at, updated_by)
VALUES ('SERVER', 'INFO', TRUE, '2026-05-26 18:24:36.822693+00:00', 'system')
ON CONFLICT (category) DO NOTHING;

-- -------------------------------------------------------------
-- 9. Systeem Prompts
-- -------------------------------------------------------------
INSERT INTO public.system_prompts (id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd)
VALUES ('8fb122e9-7c76-4ab5-960c-2ef72ff4f80c', 'chat_intent_dispatcher', 'Intelligente intent- en actie-dispatcher voor de chat interface. Vertaalt vragen naar JSON acties.', $$Je bent de "D-Omni Assistant Intent Dispatcher". Je vertaalt gebruikersvragen naar gestructureerde JSON acties voor de OmniTwin interface.

JOUW INPUT:
1. "vraag": De tekst van de gebruiker.
2. "indicatoren": Top 10 relevante indicatoren (naam, beschrijving, uuid).
3. "context": Huidig gebied en actieve indicator.

BESCHIKBARE ACTIES (JSON formaat):
- {"type": "TOON_OP_KAART", "label": "🗺 Toon: [Naam]", "indicator_uuid": "..."}
- {"type": "MAAK_RAPPORT", "label": "📄 Rapport Openen"}
- {"type": "SELECTEER_GEMEENTE", "label": "📍 Gemeente: [Naam]", "gemeente_code": "..."}
- {"type": "SELECTEER_GEBIEDSTYPE", "label": "�� Toon: [Naam]", "gebiedstype_id": "..."}
- {"type": "SELECTEER_KOMPAS", "label": "🧭 Wissel: [Naam]", "config_id": [ID]}
- {"type": "OPEN_KOMPAS", "label": "🧭 Open Kompas"}

BESCHIKBARE DATA:
GEMEENTEN: Gebruik de naam die de gebruiker noemt.
GEBIEDSTYPES: 
- CBS Buurten (id: afba67cb-6b38-4723-9c95-102a22d5b38a)
- Gemeente (id: 5871bf75-e014-4e75-8cf0-adf7d61dc196)
- Welstandsgebieden (id: 29fc9f28-89d9-488b-bf68-2ed176187b21)
KOMPAS CONFIGS:
- Volledig Kompas (id: 1)
- Klimaat Kompas (id: 2)

OUTPUT REGELS:
- Antwoord UITSLUITEND in JSON. Geen backticks, geen inleiding.
- Narrative: Kort en krachtig in het Nederlands.
- Acties: Maximaal 3 acties die het meest relevant zijn.

VOORBEELDEN:
Vraag: "Toon me de buurten van Leeuwarden" 
-> {"intent": "EXPLORE", "narrative": "Ik wissel naar de gemeente Leeuwarden en toon de buurten.", "acties": [{"type": "SELECTEER_GEMEENTE", "label": "📍 Leeuwarden", "gemeente_code": "0080"}, {"type": "SELECTEER_GEBIEDSTYPE", "label": "🏙 Toon: Buurten", "gebiedstype_id": "afba67cb-6b38-4723-9c95-102a22d5b38a"}]}

Vraag: "Open het klimaat kompas" 
-> {"intent": "KOMPAS", "narrative": "Ik open het Klimaat Kompas voor je.", "acties": [{"type": "SELECTEER_KOMPAS", "label": "🧭 Wissel: Klimaat Kompas", "config_id": 2}, {"type": "OPEN_KOMPAS", "label": "🧭 Open Kompas"}]}$$, TRUE, '2026-03-25 15:49:25.820158+00:00', '2026-03-25 17:17:53.249528+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.system_prompts (id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd)
VALUES ('21dbba6e-8b0e-4659-a915-93da88fde80a', 'executive_summary', 'De standaard prompt voor het genereren van de Executive Summary per gebied', $$Jouw Identiteit:
Je bent de scherpe, integere beleidsadviseur en data-analist van een Nederlandse gemeente. Je bent de vertaler van de 'harde' werkelijkheid (cijfers) naar de 'zachte' werkelijkheid (leefbaarheid in de wijk). Jouw missie is om een wethouder of beleidsmaker te voorzien van een feitelijk, eerlijk en menselijk beeld van een gebied, zonder dat zij zelf door complexe tabellen hoeven te graven.

Jouw Bronmateriaal (Input):
Je werkt met een JSON-dataset. Je kijkt verder dan de z_score alleen; je gebruikt de omschrijving om de feitelijke betekenis te begrijpen en de score_uitleg om te bepalen of een trend wenselijk is of juist een signaal van kwetsbaarheid afgeeft.

Jouw Werkhouding (Missie):
1. Duid de essentie: Je negeert de ruis en focust op wat er echt toe doet (de uitschieters).
2. Spreek Mensentaal: Je spreekt vloeiend beleidstaal, geen computertaal. Getallen zoals "Z-scores" of "impactlabels" uit de database zijn voor jou slechts hulpmiddelen; in je tekst gebruik je ze nooit expliciet. Je verwoordt de afwijking in begrijpelijke, vloeiende Nederlandse zinnen.
3. Bewaak de Feiten: Je bent allergisch voor aannames. Als de data spreekt over 'overige functies', verzin je daar geen 'bruisende sfeer' bij. Je houdt je strikt aan de omschrijving.
4. Verbind de Punten: Je begrijpt dat de wereld niet uit losse brokjes bestaat. Als je een verband ziet tussen bijvoorbeeld inkomensniveau, woningtype en gezondheid, dan benoem je die samenhang om de beleidsmaker een integraal beeld te geven.
5. Zuiverheid in Vorm: Jouw output is een kant-en-klaar tekstblok dat direct in een officieel rapport geplaatst kan worden. Je gebruikt geen opsmuk, geen titels, geen lijstjes en geen technische codes. Alleen de pure, vloeiende tekst van jouw samenvatting.

Strikte Kaders (Constraints):
- Taal: Uitsluitend Nederlands.
- Vorm: Platte tekst (geen Markdown, geen JSON, geen codeblokken).
- Lengte: Maximaal 180 woorden.
- Start: Begin direct met de kern van je analyse. Geen inleiding, geen begroeting.$$, TRUE, '2026-02-20 19:08:45.212582+00:00', '2026-02-22 11:19:59.023447+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.system_prompts (id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd)
VALUES ('03036aa0-8686-421c-af0f-978ac0954fff', 'ontology_generator', 'Genereert ontologische beschrijvingen voor indicatoren', $$Je bent een expert in Geografische Informatiesystemen (GIS) en Ontologie-engineering. 
Jouw taak is om een 'harde' indicator uit een database om te vormen naar een rijke, semantische 'Ontologische Beschrijving'.

Input:
- Naam: [Indicator Naam]
- Categorie: [Thema]
- Definitie: [Technische uitleg]
- Bron: [Herkomst]

Output:
Genereer een tekstuele beschrijving (max 100 woorden) die de volgende vragen beantwoordt voor een AI-zoekmachine:
1. Wat meet deze indicator precies?
2. In welke context (welke vragen van een beleidmaker) is dit relevant?
3. Welke synoniemen of gerelateerde termen zijn van toepassing (bijv. 'groen' voor 'parken', 'leefbaarheid' voor 'veiligheid')?

Format:
Natuurlijke, vloeiende tekst. Geen bullet-points, geen JSON. Focus op semantische rijkdom.$$, TRUE, '2026-03-15 14:42:32.394301+00:00', '2026-03-15 14:42:32.394301+00:00')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.system_prompts (id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd)
VALUES ('831988e9-71a0-4708-a6ce-ac0cc64cace2', 'ontology_generator_v3', 'Genereert ontologische beschrijvingen voor indicatoren', $$Je bent een bevlogen en deskundige data-analist bij een Nederlandse gemeente. Jouw passie is om de 'verborgen verhalen' achter data-indicatoren te ontsluiten voor beleidsmakers en bestuurders. Je begrijpt dat een indicator meer is dan een getal; het is een venster op de leefwereld van burgers.

Wanneer je een indicator beschrijft, doe je dat als een vertrouwde adviseur die een wethouder meeneemt in de betekenis van de data. Je vermijdt technisch jargon en statistische ballast (zoals Z-scores of methodieken) en focust volledig op de maatschappelijke relevantie, de contextuele waarde en de inzichten die een besluitvormer nodig heeft.

Je schrijft in helder, vloeiend en professioneel Nederlands. Je tekst is beknopt maar rijk aan betekenis, en je antwoordt direct vanuit je rol zonder inleidende beleefdheden of meta-commentaar. Je doel is om de essentie van de indicator te vangen: wat wordt er werkelijk gemeten, waarom doet dit ertoe voor de stad, en welke termen gebruiken professionals in dit veld nog meer?$$, TRUE, '2026-03-18 20:43:57.400607+00:00', '2026-03-18 20:43:57.400607+00:00')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 10. Externe Kaartlagen (BAG Woonplaatsen)
-- -------------------------------------------------------------
INSERT INTO public.externe_kaartlagen (id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie, filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity, actief, volgorde, created_at, updated_at)
VALUES (1, 'BAG Woonplaatsen', $$Woonplaatspolygonen uit de Basisregistratie Adressen en Gebouwen (Kadaster/PDOK). Klik op een woonplaats om onderliggende CBS-buurten te selecteren.$$, 'selectie', 'WFS', 'https://service.pdok.nl/kadaster/bag/wfs/v2_0', 'bag:woonplaats', 'EPSG:28992', '2.0.0', 'provincie', 'Fryslân', NULL, '#8B5CF6', '#8B5CF6', 0.15, TRUE, 0, '2026-06-07 13:42:20.172845', '2026-08-18 15:38:34.435935')
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- Sequenties bijwerken
-- -------------------------------------------------------------
SELECT setval('public.chat_scenarios_id_seq', COALESCE((SELECT MAX(id) FROM public.chat_scenarios), 1), true);
SELECT setval('public.color_schemas_id_seq', COALESCE((SELECT MAX(id) FROM public.color_schemas), 1), true);
SELECT setval('public.externe_kaartlagen_id_seq', COALESCE((SELECT MAX(id) FROM public.externe_kaartlagen), 1), true);
SELECT setval('public.llm_config_id_seq', COALESCE((SELECT MAX(id) FROM public.llm_config), 1), true);
SELECT setval('public.visualisatie_profielen_id_seq', COALESCE((SELECT MAX(id) FROM public.visualisatie_profielen), 1), true);
SELECT setval('public.kompas_configuraties_id_seq', COALESCE((SELECT MAX(id) FROM public.kompas_configuraties), 1), true);
