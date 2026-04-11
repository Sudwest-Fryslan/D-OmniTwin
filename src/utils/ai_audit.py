import re
from sqlalchemy.orm import Session
from sqlalchemy import text

def audit_indicator_description(desc: str) -> list:
    """
    Checkt een ontologische beschrijving op kwaliteitsproblemen.
    Returnt een lijst met gevonden issues.
    """
    if not desc:
        return ["missing"]
        
    reasons = []
    
    # 1. Check voor think tags
    if '<think>' in desc or '</think>' in desc:
        reasons.append("think_tags")
        
    # 2. Check voor Engels (heuristiek)
    english_keywords = ['the', 'this', 'indicator', 'measure', 'relevant', 'context', 'synonyms']
    low_desc = desc.lower()
    eng_match = [w for w in english_keywords if f" {w} " in f" {low_desc} "]
    if len(eng_match) >= 3:
        reasons.append(f"english_detected")
        
    # 3. Check voor technische jargon
    technical_keywords = ['owl:', 'rdf:', 'rdfs:', 'ex:', 'objectproperty', 'datatypeproperty', 'turtle', 'schema:', 'iri']
    tech_match = [w for w in technical_keywords if w in low_desc]
    if tech_match:
        reasons.append(f"tech_jargon")
        
    # 4. Check voor markdown tabellen
    if '|' in desc and '---' in desc:
        reasons.append("markdown_table")
        
    return reasons

def mark_faulty_indicators(db: Session):
    """
    Doorloopt de database en markeert indicatoren die niet voldoen aan de kwaliteitsnormen.
    """
    query = text("SELECT uuid, naam, ontologische_beschrijving FROM indicatoren WHERE ontologische_beschrijving IS NOT NULL")
    results = db.execute(query).fetchall()
    
    count = 0
    for row in results:
        uid, naam, desc = row
        issues = audit_indicator_description(desc)
        
        if issues:
            update_query = text("UPDATE indicatoren SET ontologie_status = 'audit_fout' WHERE uuid = :uuid")
            db.execute(update_query, {"uuid": uid})
            count += 1
            
    db.commit()
    return count
