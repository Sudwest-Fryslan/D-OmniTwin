import re
from sqlalchemy.orm import Session
from omnitwin.services.llm_service import LLMService

def clean_ai_output(text: str) -> str:
    """Schoont de AI output op door <think> tags en markdown te verwijderen."""
    if not text:
        return ""
    
    # 1. Verwijder de volledige <think> blokken (indien aanwezig)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. Verwijder resterende losse tags (safeguard)
    text = text.replace('<think>', '').replace('</think>', '')
    
    # 3. Verwijder markdown code blokken (```turtle, ```json, etc)
    text = re.sub(r'```[a-z]*\n?', '', text)
    text = text.replace('```', '')
    
    # 4. Verwijder overtollige witregels aan begin/eind
    return text.strip()

def generate_indicator_description(llm: LLMService, naam: str, categorie: str, omschrijving: str, bron: str) -> str:
    """
    Genereert een maatschappelijke beschrijving voor een indicator m.b.v. de 'Bron'-filosofie.
    """
    system_prompt = """Je bent een bevlogen en deskundige data-analist bij een Nederlandse gemeente. Jouw passie is om de 'verborgen verhalen' achter data-indicatoren te ontsluiten voor beleidsmakers en bestuurders. Je begrijpt dat een indicator meer is dan een getal; het is een venster op de leefwereld van burgers.

GEBRUIK DE VOLGENDE STIJL:
- Schrijf in heldere, menselijke en vloeiende Nederlandse zinnen (verhalende toon).
- Focus volledig op de maatschappelijke relevantie: waarom is dit getal belangrijk voor een wethouder of inwoner?
- Gebruik ABSOLUUT GEEN tabellen, GEEN lijstjes, GEEN bulletpoints en GEEN technische codes of jargon (zoals 'ex:', 'rdf' of 'class').
- Antwoord direct vanuit je rol. Geen inleidende teksten als "Natuurlijk" of "Hier is de beschrijving".
- Maximaal 120 woorden."""

    user_prompt = f"""Beschrijf de maatschappelijke betekenis en de context van deze indicator voor de zoekmachine van het Kompas:
Naam: {naam}
Categorie: {categorie}
Omschrijving: {omschrijving}
Bron: {bron}"""

    response = llm._call_llm(system_prompt, user_prompt, context_name=f"Utility: {naam}")
    
    raw_text = response.get("text", "")
    return clean_ai_output(raw_text)
