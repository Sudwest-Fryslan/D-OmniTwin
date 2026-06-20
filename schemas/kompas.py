"""
Kompas Pydantic Schemas
API response models voor multi-kompas configuratie systeem
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ========================================================================
# CONFIGURATIE SCHEMAS
# ========================================================================

class KompasConfiguratieBase(BaseModel):
    """Basis configuratie info"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    naam: str
    beschrijving: Optional[str] = None
    is_standaard: bool
    is_actief: bool
    icoon: str = "🌍"


class KompasConfiguratieStats(KompasConfiguratieBase):
    """Configuratie met statistieken (van v_kompas_config_stats view)"""
    aantal_themas: int
    aantal_onderdelen: int
    aantal_indicatoren: int
    aantal_scoring_regels: int


class KompasConfiguratiesResponse(BaseModel):
    """Lijst van alle configuraties"""
    configuraties: List[KompasConfiguratieStats]
    standaard_config_id: int


# ========================================================================
# HIËRARCHIE SCHEMAS (voor D3.js sunburst)
# ========================================================================

class KompasNode(BaseModel):
    """
    Generieke node voor D3.js hierarchie
    
    Gebruikt in sunburst diagram met partition layout
    """
    name: str
    value: Optional[float] = None      # Score/waarde (voor leaf nodes = indicatoren)
    color: Optional[str] = None         # HEX kleur (#22C55E, etc.)
    children: Optional[List['KompasNode']] = None
    
    # Metadata
    uuid: Optional[str] = None          # UUID (alleen voor indicatoren)
    type: str = "node"                  # "titel", "thema", "onderdeel", "indicator"
    eenheid: Optional[str] = None       # %, aantal, €, etc.
    score_type: Optional[str] = None    # Voor debug/tooltip info
    beschrijving: Optional[str] = None  # Tooltip tekst
    ontologische_beschrijving: Optional[str] = None # Uitgebreide contextuele duiding


class HierarchieResponse(BaseModel):
    """Complete hiërarchie voor sunburst (zonder gebied data)"""
    config_id: int
    config_naam: str
    config_icoon: str
    hierarchie: KompasNode
    total_indicators: int
    last_updated: datetime = Field(default_factory=datetime.now)


# ========================================================================
# GEBIED KOMPAS SCHEMAS
# ========================================================================

class GebiedKompasResponse(BaseModel):
    """Kompas data voor één specifiek gebied (met waarden)"""
    gebied_id: str
    gebied_naam: str
    config_id: int
    config_naam: str
    hierarchie: KompasNode              # Met waarden + kleuren ingevuld
    coverage_percentage: float          # % indicatoren met data
    laatste_update: datetime = Field(default_factory=datetime.now)


# ========================================================================
# INDICATOR SCHEMAS
# ========================================================================

class IndicatorScoringRegel(BaseModel):
    """Scoring regel voor één indicator"""
    indicator_uuid: str
    indicator_naam: str
    score_type: str                     # positive_ascending, positive_descending, threshold_based, custom
    inverse: bool = False
    eenheid: Optional[str] = None
    doel_waarde: Optional[float] = None
    thresholds: Optional[Dict[str, List[float]]] = None  # {"green": [0, 20], ...}
    beschrijving: Optional[str] = None


class IndicatorPathResponse(BaseModel):
    """Breadcrumb trail voor één indicator"""
    config_id: int
    indicator_uuid: str
    path: List[str]                     # ["Titel", "Thema", "Onderdeel", "Indicator"]
    full_path_string: str               # "Titel > Thema > Onderdeel > Indicator"
    indicator_details: Dict[str, Any]


# ========================================================================
# HELPER SCHEMAS
# ========================================================================

class ColorInfo(BaseModel):
    """Kleur informatie voor UI rendering"""
    hex: str                            # "#22C55E"
    rgb: tuple[int, int, int]           # (34, 197, 94)
    label: str                          # "Groen (Goed)"


class ScoreInterpretation(BaseModel):
    """Interpretatie van een score voor tooltip"""
    waarde: float
    kleur: ColorInfo
    label: str                          # "Goed", "Matig", "Slecht"
    percentiel: Optional[float] = None  # Ranking t.o.v. andere gebieden


# Rebuild model to support forward references (List['KompasNode'])
KompasNode.model_rebuild()
