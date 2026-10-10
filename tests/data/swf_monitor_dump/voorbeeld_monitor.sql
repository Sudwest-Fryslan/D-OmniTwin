--
-- Fictieve mini-dump van de database van de gebiedsmonitor (tests/test_swf_monitor_dump.py).
-- Alle namen, gebruikers, UUID's van indicatoren en waarden zijn verzonnen.
--

SET client_encoding = 'UTF8';

COPY public.gebiedstype (id, naam, sleutel, wfs, label, actief, typenames) FROM stdin;
afba67cb-6b38-4723-9c95-102a22d5b38a	CBS buurten	buurt_code	https://geo.voorbeeld.nl/wfs	buurt_naam	t	vb:buurten
d210c084-506b-48b4-87c9-b7d4bf422553	CBS buurten bebouwde komgrens	 	 	 	f	 
29fc9f28-89d9-488b-bf68-2ed176187b21	Welstand per buurt	gebieds_id	https://geo.voorbeeld.nl/wfs	gebieds_naam	t	vb:welstand
\.

COPY public.indicator (id, naam, omschrijving, status, begingeldigheid, eindgeldigheid) FROM stdin;
0e5b1c4a-1111-4aaa-8aaa-000000000001	Fictieve indicator een	Omschrijving met een tab\tin de tekst	A	2024-11-20 00:00:00	\N
0e5b1c4a-2222-4bbb-8bbb-000000000002	Fictieve indicator twee	\N	O	2024-11-20 00:00:00	2025-01-14 10:30:00
0e5b1c4a-3333-4ccc-8ccc-000000000003	Fictieve indicator drie	Drie	C	2024-11-20 00:00:00	\N
0e5b1c4a-4444-4ddd-8ddd-000000000004	Fictieve indicator vier	Vier	B	2024-11-20 00:00:00	\N
0e5b1c4a-5555-4eee-8eee-000000000005	Fictieve klimaatindicator	Klimaat	A	2024-11-20 00:00:00	\N
\.

COPY public.indicator_gebiedstype (indicator_id, gebiedstype_id) FROM stdin;
0e5b1c4a-1111-4aaa-8aaa-000000000001	afba67cb-6b38-4723-9c95-102a22d5b38a
0e5b1c4a-2222-4bbb-8bbb-000000000002	afba67cb-6b38-4723-9c95-102a22d5b38a
0e5b1c4a-2222-4bbb-8bbb-000000000002	d210c084-506b-48b4-87c9-b7d4bf422553
0e5b1c4a-3333-4ccc-8ccc-000000000003	afba67cb-6b38-4723-9c95-102a22d5b38a
0e5b1c4a-5555-4eee-8eee-000000000005	29fc9f28-89d9-488b-bf68-2ed176187b21
\.

COPY public.indicator_waarde (indicator_id, gebiedstype_id, gebieds_id, waarde, jaar) FROM stdin;
0e5b1c4a-1111-4aaa-8aaa-000000000001	afba67cb-6b38-4723-9c95-102a22d5b38a	BU99990001	12.5	2023
0e5b1c4a-1111-4aaa-8aaa-000000000001	afba67cb-6b38-4723-9c95-102a22d5b38a	BU99990002	7	2024
0e5b1c4a-1111-4aaa-8aaa-000000000001	afba67cb-6b38-4723-9c95-102a22d5b38a	BU99990001	1	0
0e5b1c4a-1111-4aaa-8aaa-000000000001	afba67cb-6b38-4723-9c95-102a22d5b38a	1199990001	3.25	2012
0e5b1c4a-2222-4bbb-8bbb-000000000002	d210c084-506b-48b4-87c9-b7d4bf422553	BU99990001_BBKJ	0.5	2022
0e5b1c4a-5555-4eee-8eee-000000000005	29fc9f28-89d9-488b-bf68-2ed176187b21	17	-12.75	2025
\.

COPY public.monitor (id, naam, gebiedstype_id, configuratie, volgnummer, begingeldigheid, eindgeldigheid, vastgelegd_door) FROM stdin;
node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa	Voorbeeld basis	afba67cb-6b38-4723-9c95-102a22d5b38a	{"id": "node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa", "naam": "Voorbeeld basis", "text": "Voorbeeld basis", "type": "root", "weergave_type": "percentiel_waarden", "gebiedstype_id": "afba67cb-6b38-4723-9c95-102a22d5b38a", "gebiedsindeling": "CBS_BUURTEN", "children": [{"id": "node_id_k1", "text": "Kwadrant een", "type": "categorie", "children": [{"id": "node_id_t1", "text": "Thema een", "type": "categorie", "children": [{"id": "node_id_o1", "text": "Onderdeel een", "type": "categorie", "children": [{"id": "node_id_i1", "text": "Fictieve indicator een", "type": "indicator", "indicator_id": "0e5b1c4a-1111-4aaa-8aaa-000000000001", "omkeren": true}, {"id": "node_id_x1", "text": "Extra niveau", "type": "categorie", "children": [{"id": "node_id_i2", "text": "Fictieve indicator twee", "type": "indicator", "indicator_id": "0e5b1c4a-2222-4bbb-8bbb-000000000002", "omkeren": false, "labeling": {"A": {"van": 0.0, "tot": 10.0, "kleur": "rgb(0, 176, 80)", "label": "Robuust"}, "B": {"van": 10.0, "tot": 20.0, "kleur": "rgb(146, 208, 80)", "label": "Acceptabel"}, "C": {"van": 20.0, "tot": 30.0, "kleur": "rgb(255, 255, 0)", "label": "Risicovol"}, "D": {"van": 30.0, "tot": 40.0, "kleur": "rgb(255, 204, 0)", "label": "Onacceptabel"}, "E": {"van": 40.0, "tot": 9999.0, "kleur": "rgb(255, 0, 0)", "label": "Ontwrichting"}}}]}]}]}]}, {"id": "node_id_k2", "text": "Kwadrant twee", "type": "categorie", "children": [{"id": "node_id_t2", "text": "Thema twee", "type": "categorie", "children": [{"id": "node_id_o2", "text": "Onderdeel twee", "type": "categorie", "children": [{"id": "node_id_i3", "text": "Fictieve indicator drie", "type": "indicator", "indicator_id": "0e5b1c4a-3333-4ccc-8ccc-000000000003"}]}]}]}]}	1	2025-04-22 12:00:00	2025-07-01 09:00:00	voorbeeld.beheerder
node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa	Voorbeeld basis	afba67cb-6b38-4723-9c95-102a22d5b38a	{"id": "node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa", "naam": "Voorbeeld basis", "text": "Voorbeeld basis", "type": "root", "weergave_type": "percentiel_waarden", "gebiedstype_id": "afba67cb-6b38-4723-9c95-102a22d5b38a", "gebiedsindeling": "CBS_BUURTEN", "children": [{"id": "node_id_k1", "text": "Kwadrant een", "type": "categorie", "children": [{"id": "node_id_t1", "text": "Thema een", "type": "categorie", "children": [{"id": "node_id_o1", "text": "Onderdeel een", "type": "categorie", "children": [{"id": "node_id_i1", "text": "Fictieve indicator een", "type": "indicator", "indicator_id": "0e5b1c4a-1111-4aaa-8aaa-000000000001", "omkeren": true}, {"id": "node_id_x1", "text": "Extra niveau", "type": "categorie", "children": [{"id": "node_id_i2", "text": "Fictieve indicator twee", "type": "indicator", "indicator_id": "0e5b1c4a-2222-4bbb-8bbb-000000000002", "omkeren": false, "labeling": {"A": {"van": 0.0, "tot": 10.0, "kleur": "rgb(0, 176, 80)", "label": "Robuust"}, "B": {"van": 10.0, "tot": 20.0, "kleur": "rgb(146, 208, 80)", "label": "Acceptabel"}, "C": {"van": 20.0, "tot": 30.0, "kleur": "rgb(255, 255, 0)", "label": "Risicovol"}, "D": {"van": 30.0, "tot": 40.0, "kleur": "rgb(255, 204, 0)", "label": "Onacceptabel"}, "E": {"van": 40.0, "tot": 9999.0, "kleur": "rgb(255, 0, 0)", "label": "Ontwrichting"}}}]}]}]}]}, {"id": "node_id_k2", "text": "Kwadrant twee", "type": "categorie", "children": [{"id": "node_id_t2", "text": "Thema twee", "type": "categorie", "children": [{"id": "node_id_o2", "text": "Onderdeel twee", "type": "categorie", "children": [{"id": "node_id_i3", "text": "Fictieve indicator drie", "type": "indicator", "indicator_id": "0e5b1c4a-3333-4ccc-8ccc-000000000003"}, {"id": "node_id_i4", "text": "Fictieve indicator vier", "type": "indicator", "indicator_id": "0e5b1c4a-4444-4ddd-8ddd-000000000004"}]}]}]}]}	2	2025-07-01 09:00:00	\N	voorbeeld.beheerder
node_id_0e5b1c4a-bbbb-4bbb-8bbb-0000000000bb	Voorbeeld klimaat	29fc9f28-89d9-488b-bf68-2ed176187b21	{"id": "node_id_0e5b1c4a-bbbb-4bbb-8bbb-0000000000bb", "naam": "Voorbeeld klimaat", "text": "Voorbeeld klimaat", "type": "root", "weergave_type": "labeling_waarden", "gebiedstype_id": "29fc9f28-89d9-488b-bf68-2ed176187b21", "gebiedsindeling": "Welstandsgebieden", "children": [{"id": "node_id_c1", "text": "Hitte", "type": "categorie", "children": [{"id": "node_id_k5", "text": "Fictieve klimaatindicator", "type": "indicator", "indicator_id": "0e5b1c4a-5555-4eee-8eee-000000000005", "omkeren": false, "labeling": {"A": {"van": 50.0, "tot": 9999.0, "label": "Robuust"}, "B": {"van": 0.0, "tot": 50.0, "label": "Acceptabel"}, "C": {"van": -50.0, "tot": 0.0, "label": "Risicovol"}, "D": {"van": -100.0, "tot": -50.0, "label": "Onacceptabel"}, "E": {"van": -100.0, "tot": -9999.0, "label": "Ontwrichting"}}}]}]}	1	2025-06-01 08:00:00	\N	voorbeeld.beheerder
\.

COPY public.user_properties (username, key, value) FROM stdin;
voorbeeld.gebruiker1	last_map_coordinate	{"center":[155000,463000],"resolution":4.5}
voorbeeld.gebruiker1	selected_node_id	node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa
voorbeeld.gebruiker1	panel_visible	true
voorbeeld.gebruiker1	active_item	Voorbeeldpaneel
voorbeeld.gebruiker1	visible_base_layer	Voorbeeldkaart
voorbeeld.gebruiker2	last_map_coordinate	{"center":[600000,6800000],"resolution":20}
voorbeeld.gebruiker2	selected_node_id	node_id_0e5b1c4a-bbbb-4bbb-8bbb-0000000000bb
voorbeeld.gebruiker3	selected_node_id	node_id_0e5b1c4a-aaaa-4aaa-8aaa-0000000000aa
voorbeeld.gebruiker3	active_item	Eenanderpaneel
\.
