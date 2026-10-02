-- v35: embeddings opnieuw berekenen als tekst of model verandert (#233)
-- tekst_hash = SHA-256 van model, revisie en de geëmbedde tekst (naam, kompaspad, eenheid,
-- synoniemen, beschrijving; services/zoektaal.py indicator_tekst). Wijkt die af, dan berekent
-- services/indicator_embeddings.py de embedding opnieuw (db-init, of na een levering).
-- Bestaande rijen krijgen NULL en worden bij de volgende db-init herberekend. Idempotent.
-- Nummer 35: 23-34 zijn vrijgehouden voor andere lopende wijzigingen (laad-API, organisatie).
ALTER TABLE indicator_embeddings
    ADD COLUMN IF NOT EXISTS tekst_hash varchar(64);

COMMENT ON COLUMN indicator_embeddings.tekst_hash IS
    'SHA-256 van model, revisie en geëmbedde tekst; anders opnieuw berekenen (#233)';
