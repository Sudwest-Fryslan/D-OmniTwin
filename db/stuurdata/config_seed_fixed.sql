--
-- PostgreSQL database dump
--

\restrict LePSohQIRbfM3OZ7kznUkBD1yHlkZRVIKSdQp7WVCwP0MhREuSGj97emzW9X8Hw

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: chat_scenarios; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.chat_scenarios (id, rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, is_actief, volgorde) FROM stdin;
2	wijkcontactfunctionaris	Dorp/Wijk contactfunctionaris	Lokale initiatieven en wijkzaken	Je hebt gekozen voor het perspectief van Dorp/Wijk contactfunctionaris. (Dit scenario wordt binnenkort verder ingevuld, je kunt de applicatie ondertussen vrij gebruiken).	[]	["wijkcontactfunctionaris", "dorpsbelang", "wijkagent"]	t	20
1	beleidsadviseur	Beleidsadviseur	Beleid & RO voor gemeenten	Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?	[{"type": "SELECTEER_GEBIEDSTYPE", "label": "🗺️ Toon: Buurten", "gebiedstype_id": "buurt"}, {"type": "SELECTEER_GEMEENTE", "label": "📍 Gemeente: Súdwest-Fryslân", "gemeente_code": "1900"}, {"type": "OPEN_KOMPAS", "label": "🧭 Open het D-Omni Kompas"}]	["beleidsadviseur", "ijsselmeerkust", "makkum", "workum"]	t	10
\.


--
-- Data for Name: color_schemas; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.color_schemas (id, naam, beschrijving, colors, is_actief, created_at, updated_at, palette_type, classificatie, klassen, nodata_kleur) FROM stdin;
9	owner-occupied home		{"max": "#08306b", "mid": "#4292c6", "min": "#deebf7"}	t	2026-02-17 15:16:11.004416	2026-02-17 15:16:11.004416	sequential	equal_interval	7	#d1d5db
3	green-brown	Groen naar bruin (natuur)	{"max": "#a16207", "mid": "#84cc16", "min": "#10b981"}	t	2026-02-01 17:24:49.99645	2026-04-12 14:50:56.866103	sequential	quantile	7	#d1d5db
4	monochrome	Grijstinten	{"max": "#e5e7eb", "mid": "#6b7280", "min": "#1f2937"}	t	2026-02-01 17:24:49.99645	2026-04-12 14:51:02.124245	sequential	quantile	7	#d1d5db
5	sequential-blue	Objectief & Feitelijk (bevolking, dichtheid, aantallen)	{"max": "#08306b", "mid": "#4292c6", "min": "#deebf7"}	t	2026-02-15 21:20:16.055088	2026-04-12 14:51:09.174136	sequential	quantile	7	#d1d5db
6	colorblind-safe	Toegankelijk oordelend (gezondheid, kwaliteit, index)	{"max": "#0077b6", "mid": "#fdf0d5", "min": "#ae2012"}	t	2026-02-15 21:20:16.055088	2026-04-12 14:51:13.966703	diverging	diverging_midpoint	7	#d1d5db
7	subjective-gold	Divergerend (enquête, beleving)	{"max": "#f59e0b", "mid": "#f3f4f6", "min": "#7c3aed"}	t	2026-02-15 21:20:16.055088	2026-04-12 14:51:18.697853	diverging	diverging_midpoint	7	#d1d5db
8	urban-density	Intensiteit (bebouwing, verkeer)	{"max": "#881337", "mid": "#fb7185", "min": "#fff1f2"}	t	2026-02-15 21:20:16.055088	2026-04-12 14:51:23.273214	sequential	jenks	7	#d1d5db
2	blue-red	Blauw naar rood	{"max": "#ef4444", "mid": "#a855f7", "min": "#3b82f6"}	t	2026-02-01 17:24:49.99645	2026-04-12 15:55:18.549698	sequential	jenks	7	#d1d5db
1	default	Standaard rood-geel-groen	{"max": "#10b981", "mid": "#fbbf24", "min": "#ef4444"}	t	2026-02-01 17:24:49.99645	2026-06-17 15:55:14.573306	sequential	jenks	7	#d1d5db
\.


--
-- Data for Name: externe_kaartlagen; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.externe_kaartlagen (id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie, filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity, actief, volgorde, created_at, updated_at) FROM stdin;
1	BAG Woonplaatsen	Woonplaatspolygonen uit de Basisregistratie Adressen en Gebouwen (Kadaster/PDOK). Klik op een woonplaats om onderliggende CBS-buurten te selecteren.	selectie	WFS	https://service.pdok.nl/kadaster/bag/wfs/v2_0	bag:woonplaats	EPSG:28992	2.0.0	provincie	Fryslân	\N	#8B5CF6	#8B5CF6	0.15	t	10	2026-06-07 13:42:20.172845	2026-06-07 13:42:20.172845
2	Omgevingsvisie SWF	Deelgebieden uit de Omgevingsvisie van Súdwest-Fryslân (6 deelgebieden)	selectie	lokaal	Deelgebieden_omgevingsvisie.gpkg	demo_gebiedsdata__deelgebieden	EPSG:28992	1.0	alles	\N	\N	#E8A838	#E8A838	0.15	t	1	2026-06-07 21:59:16.432547	2026-06-07 21:59:16.432547
\.


--
-- Data for Name: gebiedstypes; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, created_at, updated_at) FROM stdin;
afba67cb-6b38-4723-9c95-102a22d5b38a	CBS Buurten	CBS_BUURT	Buurtindelingen volgens het Centraal Bureau voor de Statistiek	CBS	Buurt	2026-01-17 00:16:01.343807	2026-01-17 00:16:01.343807
29fc9f28-89d9-488b-bf68-2ed176187b21	Welstandsgebieden	WELSTAND	Welstandsgebieden zoals gedefinieerd in de welstandsnota	Gemeente	Gebied	2026-01-17 00:16:01.343807	2026-01-17 00:16:01.343807
d210c084-506b-48b4-87c9-b7d4bf422553	Custom Gebied Type	CUSTOM	Nog te specificeren gebiedstype	Gemeente	Overig	2026-01-17 00:16:01.343807	2026-01-17 00:16:01.343807
5871bf75-e014-4e75-8cf0-adf7d61dc196	Gemeente	\N	\N	\N	\N	2026-02-11 21:19:47.544906	2026-02-11 21:19:47.544906
22401c4c-8272-4895-a0a2-a8d48a0b4c36	Provincie	PROVINCIE	Provincies van Nederland	CBS	Provincie	2026-03-17 21:17:51.205183	2026-03-17 21:17:51.205183
\.


--
-- Data for Name: gemeenten; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.gemeenten (code, naam, provincie, is_eiland, created_at, updated_at) FROM stdin;
0059	Achtkarspelen	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0060	Ameland	Fryslân	t	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
1891	Dantumadiel	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0072	Harlingen	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0074	Heerenveen	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0080	Leeuwarden	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
1970	Noardeast-Fryslân	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0085	Ooststellingwerf	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0086	Opsterland	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0088	Schiermonnikoog	Fryslân	t	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
1900	Súdwest-Fryslân	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0093	Terschelling	Fryslân	t	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0737	Tytsjerksteradiel	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0096	Vlieland	Fryslân	t	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
1949	Waadhoeke	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0098	Weststellingwerf	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-08 14:31:37.011045
0090	Smallingerland	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-11 18:53:16.43507
1940	De Fryske Marren	Fryslân	f	2026-02-08 14:31:37.011045	2026-02-11 18:53:16.467313
1969	Westerkwartier	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1699	Noordenveld	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1701	Westerveld	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1731	Midden-Drenthe	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0171	Noordoostpolder	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0118	Hoogeveen	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0119	Meppel	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1690	De Wolden	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0420	Medemblik	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1911	Hollands Kroon	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1966	Het Hogeland	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0184	Urk	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0388	Enkhuizen	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0448	Texel	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0014	Groningen	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0106	Assen	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0109	Coevorden	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0160	Hardenberg	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0180	Staphorst	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1680	Aa en Hunze	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1681	Borger-Odoorn	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1708	Steenwijkerland	Fryslân	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1730	Tynaarlo	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1952	Midden-Groningen	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1979	Eemsdelta	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1895	Oldambt	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0037	Stadskanaal	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0047	Veendam	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0114	Emmen	Drenthe	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
0765	Pekela	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
1950	Westerwolde	Groningen	f	2026-03-17 21:17:57.821877	2026-03-17 21:17:57.821877
\.


--
-- Data for Name: indicator_gebiedstype_relaties; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.indicator_gebiedstype_relaties (indicator_uuid, gebiedstype_id, verplicht, display_volgorde, created_at) FROM stdin;
\.


--
-- Data for Name: llm_config; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.llm_config (id, api_url, model_name, aangemaakt_op, bijgewerkt_op) FROM stdin;
1	http://localhost:11434	qwen3:30b	2026-02-21 12:10:29.863903+01	2026-02-21 12:10:29.863903+01
2	http://localhost:11434	gpt-oss:20b	2026-02-21 12:35:17.240268+01	2026-02-21 12:35:17.240268+01
3	http://localhost:11434	deepseek-r1:latest	2026-02-21 18:34:19.322473+01	2026-02-21 18:34:19.322473+01
4	http://localhost:11434	qwen3:30b	2026-02-21 19:03:34.974567+01	2026-02-21 19:03:34.974567+01
5	http://localhost:11434	gpt-oss:20b	2026-02-21 19:14:24.407573+01	2026-02-21 19:14:24.407573+01
6	http://localhost:11434	qwen3.5:9b	2026-03-29 21:44:43.004905+02	2026-03-29 21:44:43.004905+02
7	http://localhost:11434	gpt-oss:20b	2026-03-29 22:00:42.540578+02	2026-03-29 22:00:42.540578+02
8	http://localhost:11434	gpt-oss:20b	2026-04-02 17:01:57.580572+02	2026-04-02 17:01:57.580572+02
9	http://localhost:11434	qwen3.5:9b	2026-04-02 21:07:43.370978+02	2026-04-02 21:07:43.370978+02
10	http://localhost:11434	gpt-oss:20b	2026-04-03 11:10:39.003801+02	2026-04-03 11:10:39.003801+02
11	http://localhost:11434	qwen3.5:9b	2026-04-03 12:29:00.835002+02	2026-04-03 12:29:00.835002+02
12	http://localhost:11434	gpt-oss:20b	2026-04-03 12:34:52.831697+02	2026-04-03 12:34:52.831697+02
13	http://localhost:11434	mistral-nemo:latest	2026-04-03 12:37:50.123328+02	2026-04-03 12:37:50.123328+02
14	http://localhost:11434	gemma4:e4b	2026-04-05 18:10:59.097611+02	2026-04-05 18:10:59.097611+02
\.


--
-- Data for Name: log_config; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.log_config (category, level, enabled, updated_at, updated_by) FROM stdin;
SERVER	INFO	t	2026-05-26 20:24:36.822693+02	system
API	INFO	t	2026-05-26 20:24:36.822693+02	system
AUTH	WARNING	t	2026-05-26 20:24:36.822693+02	system
KOMPAS	INFO	t	2026-05-26 20:24:36.822693+02	system
KAART	INFO	t	2026-05-26 20:24:36.822693+02	system
RAPPORT	INFO	t	2026-05-26 20:24:36.822693+02	system
LLM_CHAT	WARNING	t	2026-05-26 20:24:36.822693+02	system
DATABASE	WARNING	t	2026-05-26 20:24:36.822693+02	system
ADMIN	INFO	t	2026-05-26 20:24:36.822693+02	system
\.


--
-- Data for Name: system_prompts; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.system_prompts (id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd) FROM stdin;
21dbba6e-8b0e-4659-a915-93da88fde80a	executive_summary	De standaard prompt voor het genereren van de Executive Summary per gebied	Jouw Identiteit:\nJe bent de scherpe, integere beleidsadviseur en data-analist van een Nederlandse gemeente. Je bent de vertaler van de 'harde' werkelijkheid (cijfers) naar de 'zachte' werkelijkheid (leefbaarheid in de wijk). Jouw missie is om een wethouder of beleidsmaker te voorzien van een feitelijk, eerlijk en menselijk beeld van een gebied, zonder dat zij zelf door complexe tabellen hoeven te graven.\n\nJouw Bronmateriaal (Input):\nJe werkt met een JSON-dataset. Je kijkt verder dan de z_score alleen; je gebruikt de omschrijving om de feitelijke betekenis te begrijpen en de score_uitleg om te bepalen of een trend wenselijk is of juist een signaal van kwetsbaarheid afgeeft.\n\nJouw Werkhouding (Missie):\n1. Duid de essentie: Je negeert de ruis en focust op wat er echt toe doet (de uitschieters).\n2. Spreek Mensentaal: Je spreekt vloeiend beleidstaal, geen computertaal. Getallen zoals "Z-scores" of "impactlabels" uit de database zijn voor jou slechts hulpmiddelen; in je tekst gebruik je ze nooit expliciet. Je verwoordt de afwijking in begrijpelijke, vloeiende Nederlandse zinnen.\n3. Bewaak de Feiten: Je bent allergisch voor aannames. Als de data spreekt over 'overige functies', verzin je daar geen 'bruisende sfeer' bij. Je houdt je strikt aan de omschrijving.\n4. Verbind de Punten: Je begrijpt dat de wereld niet uit losse brokjes bestaat. Als je een verband ziet tussen bijvoorbeeld inkomensniveau, woningtype en gezondheid, dan benoem je die samenhang om de beleidsmaker een integraal beeld te geven.\n5. Zuiverheid in Vorm: Jouw output is een kant-en-klaar tekstblok dat direct in een officieel rapport geplaatst kan worden. Je gebruikt geen opsmuk, geen titels, geen lijstjes en geen technische codes. Alleen de pure, vloeiende tekst van jouw samenvatting.\n\nStrikte Kaders (Constraints):\n- Taal: Uitsluitend Nederlands.\n- Vorm: Platte tekst (geen Markdown, geen JSON, geen codeblokken).\n- Lengte: Maximaal 180 woorden.\n- Start: Begin direct met de kern van je analyse. Geen inleiding, geen begroeting.	t	2026-02-20 20:08:45.212582+01	2026-02-22 12:19:59.023447+01
03036aa0-8686-421c-af0f-978ac0954fff	ontology_generator	Genereert ontologische beschrijvingen voor indicatoren	Je bent een expert in Geografische Informatiesystemen (GIS) en Ontologie-engineering. \nJouw taak is om een 'harde' indicator uit een database om te vormen naar een rijke, semantische 'Ontologische Beschrijving'.\n\nInput:\n- Naam: [Indicator Naam]\n- Categorie: [Thema]\n- Definitie: [Technische uitleg]\n- Bron: [Herkomst]\n\nOutput:\nGenereer een tekstuele beschrijving (max 100 woorden) die de volgende vragen beantwoordt voor een AI-zoekmachine:\n1. Wat meet deze indicator precies?\n2. In welke context (welke vragen van een beleidmaker) is dit relevant?\n3. Welke synoniemen of gerelateerde termen zijn van toepassing (bijv. 'groen' voor 'parken', 'leefbaarheid' voor 'veiligheid')?\n\nFormat:\nNatuurlijke, vloeiende tekst. Geen bullet-points, geen JSON. Focus op semantische rijkdom.	t	2026-03-15 15:42:32.394301+01	2026-03-15 15:42:32.394301+01
831988e9-71a0-4708-a6ce-ac0cc64cace2	ontology_generator_v3	Genereert ontologische beschrijvingen voor indicatoren	Je bent een bevlogen en deskundige data-analist bij een Nederlandse gemeente. Jouw passie is om de 'verborgen verhalen' achter data-indicatoren te ontsluiten voor beleidsmakers en bestuurders. Je begrijpt dat een indicator meer is dan een getal; het is een venster op de leefwereld van burgers.\n\nWanneer je een indicator beschrijft, doe je dat als een vertrouwde adviseur die een wethouder meeneemt in de betekenis van de data. Je vermijdt technisch jargon en statistische ballast (zoals Z-scores of methodieken) en focust volledig op de maatschappelijke relevantie, de contextuele waarde en de inzichten die een besluitvormer nodig heeft.\n\nJe schrijft in helder, vloeiend en professioneel Nederlands. Je tekst is beknopt maar rijk aan betekenis, en je antwoordt direct vanuit je rol zonder inleidende beleefdheden of meta-commentaar. Je doel is om de essentie van de indicator te vangen: wat wordt er werkelijk gemeten, waarom doet dit ertoe voor de stad, en welke termen gebruiken professionals in dit veld nog meer?	t	2026-03-18 21:43:57.400607+01	2026-03-18 21:43:57.400607+01
8fb122e9-7c76-4ab5-960c-2ef72ff4f80c	chat_intent_dispatcher	Intelligente intent- en actie-dispatcher voor de chat interface. Vertaalt vragen naar JSON acties.	Je bent de "D-Omni Assistant Intent Dispatcher". Je vertaalt gebruikersvragen naar gestructureerde JSON acties voor de OmniTwin interface.\n\nJOUW INPUT:\n1. "vraag": De tekst van de gebruiker.\n2. "indicatoren": Top 10 relevante indicatoren (naam, beschrijving, uuid).\n3. "context": Huidig gebied en actieve indicator.\n\nBESCHIKBARE ACTIES (JSON formaat):\n- {"type": "TOON_OP_KAART", "label": "🗺 Toon: [Naam]", "indicator_uuid": "..."}\n- {"type": "MAAK_RAPPORT", "label": "📄 Rapport Openen"}\n- {"type": "SELECTEER_GEMEENTE", "label": "📍 Gemeente: [Naam]", "gemeente_code": "..."}\n- {"type": "SELECTEER_GEBIEDSTYPE", "label": "�� Toon: [Naam]", "gebiedstype_id": "..."}\n- {"type": "SELECTEER_KOMPAS", "label": "🧭 Wissel: [Naam]", "config_id": [ID]}\n- {"type": "OPEN_KOMPAS", "label": "🧭 Open Kompas"}\n\nBESCHIKBARE DATA:\nGEMEENTEN: Gebruik de naam die de gebruiker noemt.\nGEBIEDSTYPES: \n- CBS Buurten (id: afba67cb-6b38-4723-9c95-102a22d5b38a)\n- Gemeente (id: 5871bf75-e014-4e75-8cf0-adf7d61dc196)\n- Welstandsgebieden (id: 29fc9f28-89d9-488b-bf68-2ed176187b21)\nKOMPAS CONFIGS:\n- Volledig Kompas (id: 1)\n- Klimaat Kompas (id: 2)\n\nOUTPUT REGELS:\n- Antwoord UITSLUITEND in JSON. Geen backticks, geen inleiding.\n- Narrative: Kort en krachtig in het Nederlands.\n- Acties: Maximaal 3 acties die het meest relevant zijn.\n\nVOORBEELDEN:\nVraag: "Toon me de buurten van Leeuwarden" \n-> {"intent": "EXPLORE", "narrative": "Ik wissel naar de gemeente Leeuwarden en toon de buurten.", "acties": [{"type": "SELECTEER_GEMEENTE", "label": "📍 Leeuwarden", "gemeente_code": "0080"}, {"type": "SELECTEER_GEBIEDSTYPE", "label": "🏙 Toon: Buurten", "gebiedstype_id": "afba67cb-6b38-4723-9c95-102a22d5b38a"}]}\n\nVraag: "Open het klimaat kompas" \n-> {"intent": "KOMPAS", "narrative": "Ik open het Klimaat Kompas voor je.", "acties": [{"type": "SELECTEER_KOMPAS", "label": "🧭 Wissel: Klimaat Kompas", "config_id": 2}, {"type": "OPEN_KOMPAS", "label": "🧭 Open Kompas"}]}	t	2026-03-25 16:49:25.820158+01	2026-03-25 18:17:53.249528+01
\.


--
-- Data for Name: visualisatie_profielen; Type: TABLE DATA; Schema: public; Owner: omnitwin_user
--

COPY public.visualisatie_profielen (id, naam, beschrijving, indicator_pattern, color_schema_id, classificatie_override, klassen_override, midpoint_waarde, is_actief, created_at, updated_at) FROM stdin;
2	Dichtheid	Dichtheidsmetingen per oppervlakte	%dichtheid%	5	jenks	5	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:20:16.075691
3	Percentage	Percentuele indicatoren	%pct_%	6	quantile	5	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:20:16.075691
4	Index Score	Index en score waarden	%index%	6	diverging_midpoint	5	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:20:16.075691
5	Bouwjaar	Bouwperiode gerelateerde indicatoren	%bouwjaar%	5	equal_interval	5	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:20:16.075691
6	Gezondheid	RIVM gezondheidsmonitoring indicatoren	%gezond%	6	quantile	5	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:20:16.075691
1	Bevolking	Bevolkingsaantallen en demografische data	%inwoner%	5	quantile	7	\N	t	2026-02-15 21:20:16.075691	2026-02-15 21:53:30.872717
7	profiel_vrijwilliger	Vrijwilligerswerk	Vrijwilliger%	7	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
8	profiel_koop	Koopwoningen	Koopwoningen%	5	equal_interval	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
9	profiel_mantelzorg	Mantelzorg	Mantelzorger%	7	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
10	profiel_woningmarkt	Woningmarkt breed	%woning%	5	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
11	profiel_diefstal	Diefstal	%diefstal%	8	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
12	profiel_opleiding	Opleidingsniveau	Opleidingsniveau%	5	equal_interval	5	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
13	profiel_particulier	Particulier huurbezit	Particulier%	5	equal_interval	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
14	profiel_inwoners	Inwonersaantallen	Inwoners%	5	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
15	profiel_inkomen	Inkomensindicatoren	%inkomen%	6	diverging_midpoint	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
16	profiel_eenzaamheid	Eenzaamheid	Eenzaam%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
17	profiel_eigendom	Woningeigendom corporatie	Woningcorporatie%	5	equal_interval	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
18	profiel_woz	WOZ-waarden	%WOZ%	5	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
19	profiel_standaard	Standaard catch-all	%	1	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
20	profiel_groen	Groene leefomgeving	%groen%	3	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
21	profiel_woningvoorraat	Woningvoorraad	Woningvoorraad%	5	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
22	profiel_dichtheid	Bevolkingsdichtheid	Bevolkingsdichtheid%	5	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
23	profiel_grondwater	Grondwater	%grondwater%	3	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
24	profiel_laag_inkomen	Laag inkomen huishoudens	Huishoudens met laag%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
25	profiel_ervaren_gez	Ervaren gezondheid	Ervaren%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
26	profiel_rondkomen	Moeite met rondkomen	Moeite met%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
27	profiel_gevoelstemp	Gevoelstemperatuur	Gevoelstemperatuur%	8	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
28	profiel_afstand	Afstand tot voorzieningen	Afstand tot%	1	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
29	profiel_inbraak	Inbraak diefstal	%inbraak%	8	jenks	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
30	profiel_bijstand	Participatiewet bijstand	Participatiewet%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
31	profiel_leeftijd	Leeftijdsgroepen	%-% jaar	5	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
32	profiel_overgewicht	Overgewicht	Overgewicht%	8	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
33	profiel_minima	Minima armoedindicatoren	Minima%	6	quantile	7	\N	t	2026-04-22 23:59:30.284282	2026-04-22 23:59:30.284282
\.


--
-- Name: chat_scenarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: omnitwin_user
--

SELECT pg_catalog.setval('public.chat_scenarios_id_seq', 2, true);


--
-- Name: color_schemas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: omnitwin_user
--

SELECT pg_catalog.setval('public.color_schemas_id_seq', 9, true);


--
-- Name: externe_kaartlagen_id_seq; Type: SEQUENCE SET; Schema: public; Owner: omnitwin_user
--

SELECT pg_catalog.setval('public.externe_kaartlagen_id_seq', 2, true);


--
-- Name: llm_config_id_seq; Type: SEQUENCE SET; Schema: public; Owner: omnitwin_user
--

SELECT pg_catalog.setval('public.llm_config_id_seq', 14, true);


--
-- Name: visualisatie_profielen_id_seq; Type: SEQUENCE SET; Schema: public; Owner: omnitwin_user
--

SELECT pg_catalog.setval('public.visualisatie_profielen_id_seq', 33, true);


--
-- PostgreSQL database dump complete
--

\unrestrict LePSohQIRbfM3OZ7kznUkBD1yHlkZRVIKSdQp7WVCwP0MhREuSGj97emzW9X8Hw

