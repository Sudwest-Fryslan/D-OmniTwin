-- ============================================================
-- Migratie v49: polariteit en naam indicator angst en depressie (#498)
--
-- Indicator 311a6449-b145-4678-b51e-ac4e342dd1bf (HoogRisicoAngststoornisOfDepressie_14
-- uit RIVM/CBS StatLine 50150NED) stond geregistreerd onder de misleidende naam
-- 'Gezondheid' met polariteit 'hoger_is_beter'.
--
-- Trigger trg_indicator_polariteit (V046) synchroniseert score_type ('+/-') en
-- interpretatie_logica ('-/+') automatisch zodra polariteit wijzigt naar 'lager_is_beter'.
--
-- Idempotent; volgt het search_path (#137).
-- ============================================================

UPDATE indicatoren
   SET naam = 'Hoog risico op angststoornis of depressie',
       polariteit = 'lager_is_beter'
 WHERE uuid = '311a6449-b145-4678-b51e-ac4e342dd1bf'::uuid
   AND (naam IS DISTINCT FROM 'Hoog risico op angststoornis of depressie'
        OR polariteit IS DISTINCT FROM 'lager_is_beter');
