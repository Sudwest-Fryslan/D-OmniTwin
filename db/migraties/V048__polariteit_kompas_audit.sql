-- ============================================================
-- Migratie v48: polariteit-audit van de Kompas-indicatoren (#441)
--
-- Bij het inladen van de SWF-monitorexport (omkeren = false als standaard in
-- de oude monitorboom) zijn diverse risico-, overlast-, ziekte-, armoede- en
-- afstand-indicatoren op 'hoger_is_beter' komen te staan. Daarnaast stonden
-- beschrijvende samenstellingsindicatoren (demografie en bebouwing) deels op
-- 'hoger_is_beter' in plaats van 'neutraal'.
--
-- De trigger trg_indicator_polariteit (V046) synchroniseert score_type en
-- interpretatie_logica automatisch zodra polariteit wijzigt.
-- Idempotent; geen schemanaam zodat search_path gevolgd wordt (#137).
-- ============================================================

-- 1. Normatieve indicatoren waarbij een lagere waarde gunstiger is ('lager_is_beter')
UPDATE indicatoren
   SET polariteit = 'lager_is_beter'
 WHERE polariteit IS DISTINCT FROM 'lager_is_beter'
   AND uuid IN (
       -- Fysieke leefomgeving: hittestress, overlast, energielabelscore (1=A+++++ .. 9=G)
       'fdb4c11b-60ca-4ea1-86b8-6855a83344ee'::uuid, -- Gevoelstemperatuur
       '3c2d0ca0-3a6d-4f53-809f-f82fa9b9fd22'::uuid, -- Gemiddeld energielabel (score 1..9)
       '4a4e9cb6-ef0d-4b29-9d26-bc19eda0339e'::uuid, -- Bekladdingen
       '5c75d4a3-3ace-4c95-a051-7040defecefa'::uuid, -- Hondenpoep
       '90c18e2b-c164-4a59-83fe-367e64fceec2'::uuid, -- Overlast weer
       '055d550f-2af8-44cd-87c5-13afdf9aa38f'::uuid, -- Rommel
       '13fa6584-2935-4209-bbe3-da04706d4c3e'::uuid, -- Vernielingen
       'c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3'::uuid, -- Waterdiepte op straat
       'b0e5ad11-8f42-4733-8e1a-0e5407e6c5fb'::uuid, -- Overlast autoverkeer
       '8ce45dd7-e60d-4356-814e-4e9fe519bf07'::uuid, -- Overlast gestalde fietsen
       'a6e0c52d-c214-4f66-9548-3ee43dd06826'::uuid, -- Parkeerdruk
       '55ba59c5-19fe-4de3-97f2-97422b4b4f3b'::uuid, -- Verkeersongevallen
       '0365aba9-4555-44c9-86a4-3d532d2e5433'::uuid, -- Incourante eensgezins
       'e5a1cf06-6119-4a75-a78b-793ac63da9c4'::uuid, -- Verhuiswens
       -- Sociale leefomgeving: overlast, onveiligheid, afstanden (km)
       '10c6d4df-44ef-4eb8-b4ab-8987012b7b16'::uuid, -- Discriminatie
       '7524a0df-fc76-4755-a855-cbcb368a43be'::uuid, -- dronken personen
       '6d56f7bc-aaf6-441e-a423-f19b3a825a79'::uuid, -- gevoel onveilig
       '784f5a85-7dcc-43fe-89a1-df4df500e34a'::uuid, -- Geweld
       '379cd3a8-409e-499d-beac-02682fd13bcf'::uuid, -- idee bedreiging
       '6f354ae4-db0a-4645-bec6-8218b4ab572d'::uuid, -- idee lastigvallen
       '3fa946ce-b007-4748-9fab-c838c7ccb9dc'::uuid, -- omwonenden (overlast)
       'ee076c87-95e8-4f5a-a753-e31fc05a0eb8'::uuid, -- wonen (overlast)
       '3d5f1d64-0e67-493c-8213-b20f07fd699f'::uuid, -- Cafetaria (afstand km)
       '0ed37b61-f13d-446b-b108-70bb09af98e0'::uuid, -- Huisarts (afstand km)
       -- Kwaliteit van leven: gezondheidsrisico's, beperkingen, armoede & uitkeringen
       'c7534c64-b1ad-4100-ba3e-58d8d8fae9d2'::uuid, -- Alcohol
       '3c09922b-98ac-448c-8384-d7b8b10f15a7'::uuid, -- Belemmerd
       '69616648-298a-493e-8264-57b5756e6fb7'::uuid, -- Beperking
       '6784d8c0-5439-4be4-9a83-8a926a4a1484'::uuid, -- Beperking gehoord
       '95cfcccd-8bf1-4b72-8ebe-03a09aaf529b'::uuid, -- Beperking zicht
       '3dee52f6-edfb-4fe9-9abe-f222315d954f'::uuid, -- Beperkte functionaliteit
       'babc4c46-d1c1-444c-af11-2bc1154af66d'::uuid, -- Chronische aandoening, 2 of meer
       '0432fef2-83f2-4405-a457-08b89945ca86'::uuid, -- Obesitas
       '34e36ae1-4132-4555-a4fc-d16b039d467e'::uuid, -- Overgewicht
       '1ed22149-7fed-4466-a3b8-dfd7ff28f5b5'::uuid, -- Overmatig drinken
       'a4780646-844e-4221-b07a-b4f4ade25059'::uuid, -- Roken
       '3dd70913-391e-4d5f-a121-d17c8b466372'::uuid, -- Huishoudens met laag inkomen
       '2e6a3139-e3a8-4565-9172-a2e9ff9347c7'::uuid, -- Minima huish met kinderen
       'e6026bbf-0e0d-4c2c-870d-29810b248bcf'::uuid, -- Minima huishouden
       '6dbbd65f-492b-4a80-b6c0-acdef412f0b1'::uuid, -- Minima kinderen
       '1f5e5ca4-2491-4e64-a587-33181d1635aa'::uuid, -- Minima personen
       '58fc72b6-881e-4917-83de-8099df3e3b0d'::uuid, -- Moeite met rondkomen
       '1d7c7beb-45b2-406d-ab0a-3580e28e782f'::uuid, -- Participatiewet 5+ jaar
       'aa5ce990-a43e-439a-9e98-69899321cf40'::uuid, -- Participatiewet totaal
       'd7c79eb2-b8a2-4949-91c5-caf7fefb89ba'::uuid, -- Werkloos totaal
       '05960c54-67c3-4760-8d8e-035d7bc4748e'::uuid  -- Werkloze jongeren
   );

-- 2. Beschrijvende indicatoren die uitsluitend onder het kwadrant Samenstelling vallen ('neutraal')
UPDATE indicatoren i
   SET polariteit = 'neutraal'
 WHERE i.polariteit IS DISTINCT FROM 'neutraal'
   AND EXISTS (
       SELECT 1
         FROM v_kompas_hierarchie vkh
        WHERE vkh.indicator_uuid = i.uuid
          AND lower(vkh.titel_naam) LIKE '%samenstelling%'
   )
   AND NOT EXISTS (
       SELECT 1
         FROM v_kompas_hierarchie vkh2
        WHERE vkh2.indicator_uuid = i.uuid
          AND lower(vkh2.titel_naam) NOT LIKE '%samenstelling%'
   );

-- 3. Typfout in themanaam 'Veilgheid' -> 'Veiligheid' corrigeren
UPDATE kompas_themas kth
   SET naam = 'Veiligheid'
 WHERE kth.naam = 'Veilgheid'
   AND NOT EXISTS (
       SELECT 1
         FROM kompas_themas kth2
        WHERE kth2.titel_id = kth.titel_id
          AND kth2.naam = 'Veiligheid'
   );

