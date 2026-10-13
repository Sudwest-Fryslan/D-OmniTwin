import json
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

# Voeg src/ (pakket omnitwin) toe aan python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root / "src"))

import re

from omnitwin import ai_vrijgave
from omnitwin.database import SessionLocal
from omnitwin.services.llm_service import LLMService
from omnitwin.utils.ai_generator import generate_indicator_description


def clean_ai_output(text: str) -> str:
    """Verwijdert ongewenste AI-artefacten zoals <think> blokken en markdown codeblokken."""
    if not text:
        return ""
    # Verwijder <think>...</think> blokken
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Verwijder markdown codeblokken
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Verwijder resterende tags (zonder inhoud te wissen)
    text = re.sub(r"<[^>]+>", "", text)
    # Trim witruimte
    return text.strip()


def ensure_system_prompt(db: Session):
    """
    Zorgt dat de v4 'Identity' prompt in de database staat voor naslag,
    ook al gebruikt het script de utility code.
    """
    prompt_name = "ontology_generator_v4"
    prompt_text = """Je bent een bevlogen en deskundige data-analist bij een Nederlandse gemeente. Jouw passie is om de 'verborgen verhalen' achter data-indicatoren te ontsluiten voor beleidsmakers en bestuurders. Je begrijpt dat een indicator meer is dan een getal; het is een venster op de leefwereld van burgers.

GEBRUIK DE VOLGENDE STIJL:
- Schrijf in heldere, menselijke en vloeiende Nederlandse zinnen (verhalende toon).
- Focus volledig op de maatschappelijke relevantie: waarom is dit getal belangrijk voor een wethouder of inwoner?
- Gebruik ABSOLUUT GEEN tabellen, GEEN lijstjes, GEEN bulletpoints en GEEN technische codes of jargon (zoals 'ex:', 'rdf' of 'class').
- Antwoord direct vanuit je rol. Geen inleidende teksten als "Natuurlijk" of "Hier is de beschrijving".
- Maximaal 120 woorden."""

    check_query = text("SELECT id FROM system_prompts WHERE naam = :naam")
    exists = db.execute(check_query, {"naam": prompt_name}).fetchone()

    if not exists:
        insert_query = text("""
            INSERT INTO system_prompts (naam, prompt_text, is_actief)
            VALUES (:naam, :text, true)
        """)
        db.execute(insert_query, {"naam": prompt_name, "text": prompt_text})
        db.commit()
        print(f"✅ System prompt '{prompt_name}' toegevoegd aan database.")


def process_indicators():
    """Main loop om indicatoren te verwerken."""
    # Ontologie genereren valt niet onder AI-usecase A, B of C (#307): staat uit
    if not ai_vrijgave.poort(
        ai_vrijgave.BUITEN, "Ontologie genereren", taak="Beschrijvingen van indicatoren genereren"
    ):
        print(ai_vrijgave.melding(ai_vrijgave.BUITEN))
        sys.exit(1)
    db = SessionLocal()
    llm = LLMService(db)

    # Gebruik de v4 prompt/logger uit de utility
    ensure_system_prompt(db)

    # Query voor 'draft' of geflagde audit fouten
    query = text("""
        SELECT uuid, naam, categorie, omschrijving, bron
        FROM indicatoren
        WHERE ontologie_status IN ('draft', 'audit_fout')
    """)

    results = db.execute(query).fetchall()

    if not results:
        print("Geen indicatoren gevonden met status 'draft' of 'audit_fout'.")
        return

    print(f"🚀 Start verrijking van {len(results)} indicatoren...")

    for row in results:
        uid, naam, categorie, omschrijving, bron = row
        print(f"--- Verwerken: {naam} ({categorie}) ---")

        # Gebruik de geborgde utility logica
        description = generate_indicator_description(llm, naam, categorie, omschrijving, bron)

        if description:
            update_query = text("""
                UPDATE indicatoren
                SET ontologische_beschrijving = :desc,
                    ontologie_status = 'beoordeeld_ai_herstel',
                    updated_at = CURRENT_TIMESTAMP
                WHERE uuid = :uuid
            """)
            db.execute(update_query, {"desc": description, "uuid": uid})
            db.commit()
            print(f"✅ Opgeslagen voor {naam}")
        else:
            print(f"⚠️ Geen output gegenereerd voor {naam}")

    print("\n🏁 Klaar met alle indicatoren.")


if __name__ == "__main__":
    process_indicators()
