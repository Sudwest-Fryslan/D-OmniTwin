-- Gebiedstypen voor de SWF-gebiedsindelingen, ook zonder de SWF-definities (#222). Idempotent.
--
-- De use case swf-gebiedsindelingen laadt woonplaatsen, postcodes en deelgebieden uit open bronnen of
-- de repo. Zonder de export van de monitor (SWF_DUMP_DIR, use case swf-definities) bestonden hun
-- gebiedstypen niet en keurde de laad-API die leveringen af (gebiedstype-onbekend). Zelfde UUID's en
-- codes als in de SWF-monitor (usecases/swf-definities/gebiedstypen.json); deelgebieden en
-- coördinatorgebieden zijn eigen gebiedstypen van D-OmniTwin. Levert swf-definities ze later, dan
-- werkt die levering naam en metadata bij.

INSERT INTO public.gebiedstypes (id, naam, code, beschrijving, bron, niveau, metadata) VALUES
    ('c2760b82-13e2-4a12-bd7c-2d6ab1fbdb49', 'BAG woonplaats', 'BAG_WOONPLAATS',
     'Woonplaatsen uit de Basisregistratie Adressen en Gebouwen (PDOK)', 'Kadaster', 'Woonplaats',
     '{"code_prefix": "WP", "gebiedsindeling_dataset": "swf-gebied-woonplaats"}'),
    ('e9255451-7476-4413-a712-e920cd2e90a8', 'Postcode (PC4)', 'POSTCODE_SWF',
     'Postcodegebieden op 4 cijfers (CBS, PDOK)', 'CBS', 'Postcode',
     '{"code_prefix": "PC", "gebiedsindeling_dataset": "swf-gebied-postcode"}'),
    ('92915ac7-fec3-49ac-a0fb-ddb9b8c92317', 'SWF bebouwde komgrens natuurwet', 'SWF_BEBOUWDE_KOM',
     'Bebouwde kom volgens de Wet natuurbescherming (gemeente Súdwest-Fryslân)', 'Gemeente', 'Kern',
     '{"code_prefix": "BK", "gebiedsindeling_dataset": "swf-gebied-bebouwde-kom"}'),
    ('e7ebeee1-fe68-5731-a112-ee82f5a37f1b', 'Deelgebieden Omgevingsvisie', 'SWF_DEELGEBIED',
     'De zes deelgebieden van de Omgevingsvisie van Súdwest-Fryslân', 'Gemeente', 'Deelgebied',
     '{"code_prefix": "DG", "gebiedsindeling_dataset": "swf-gebied-deelgebieden"}'),
    ('cbbbb563-e23f-59e2-a157-1ddfe55f32d0', 'Dorps- en wijkcoördinatorgebieden', 'SWF_COORDINATOR',
     'Werkgebieden van de dorps- en wijkcoördinatoren (gemeente Súdwest-Fryslân)', 'Gemeente', 'Werkgebied',
     '{"code_prefix": "CO", "gebiedsindeling_dataset": "swf-gebied-coordinatorgebieden"}')
ON CONFLICT (id) DO NOTHING;
