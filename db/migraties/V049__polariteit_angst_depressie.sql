-- ============================================================
-- Migratie v49: polariteit, naam en metadata indicator angst en depressie (#498)
--
-- Indicator 311a6449-b145-4678-b51e-ac4e342dd1bf (HoogRisicoAngststoornisOfDepressie_14
-- uit RIVM/CBS StatLine 50150NED, code GGADA203) stond geregistreerd onder de
-- misleidende naam 'Gezondheid' met polariteit 'hoger_is_beter' en een verouderde
-- ontologische beschrijving.
--
-- Trigger trg_indicator_polariteit (V046) synchroniseert score_type ('+/-') en
-- interpretatie_logica ('-/+') automatisch zodra polariteit wijzigt naar 'lager_is_beter'.
--
-- Idempotent; volgt het search_path (#137).
-- ============================================================

UPDATE indicatoren
   SET naam = 'Hoog risico op angststoornis of depressie',
       polariteit = 'lager_is_beter',
       eenheid = '%',
       omschrijving = 'Percentage personen van 18 jaar of ouder met een hoog risico op een angststoornis of depressie, gebaseerd op de Kessler-10 (K10) screeningsvragenlijst (score 30-50) uit de Gezondheidsmonitor Volwassenen en Ouderen (GGD, CBS en RIVM; StatLine 50150NED, code GGADA203).',
       ontologische_beschrijving = 'De indicator “Hoog risico op angststoornis of depressie” meet het geschatte percentage inwoners van 18 jaar en ouder met een verhoogd risico op psychische klachten, gebaseerd op de Kessler-10 (K10) screeningsvragenlijst uit de Gezondheidsmonitor van GGD, CBS en RIVM. Gemeenten en GGD''en gebruiken dit cijfer om mentale gezondheid en psychosociale kwetsbaarheid per wijk en buurt in kaart te brengen en gericht in te zetten op preventie en welzijnsvoorzieningen.',
       beschrijving_ai = 'De indicator “Hoog risico op angststoornis of depressie” meet het geschatte percentage inwoners van 18 jaar en ouder met een verhoogd risico op psychische klachten, gebaseerd op de Kessler-10 (K10) screeningsvragenlijst uit de Gezondheidsmonitor van GGD, CBS en RIVM. Gemeenten en GGD''en gebruiken dit cijfer om mentale gezondheid en psychosociale kwetsbaarheid per wijk en buurt in kaart te brengen en gericht in te zetten op preventie en welzijnsvoorzieningen.'
 WHERE uuid = '311a6449-b145-4678-b51e-ac4e342dd1bf'::uuid;

