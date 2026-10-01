# Pydantic Schemas voor Gebiedsmonitor API
from uuid import UUID

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Gebiedstypes
# ============================================================================

class GebiedstypeBase(BaseModel):
    naam: str
    code: Optional[str] = None
    beschrijving: Optional[str] = None
    bron: Optional[str] = None
    niveau: Optional[str] = None


class GebiedstypeResponse(GebiedstypeBase):
    id: UUID
    aantal_gebieden: Optional[int] = 0
    
    class Config:
        from_attributes = True


class GebiedstypesListResponse(BaseModel):
    gebiedstypes: List[GebiedstypeResponse]


# ============================================================================
# Gebieden
# ============================================================================

class GebiedBase(BaseModel):
    id: str
    naam: str
    gebiedstype_naam: Optional[str] = None
    heeft_data: bool = False
    aantal_indicatoren: int = 0


class GebiedDetail(BaseModel):
    id: str
    naam: str
    gebiedstype: Dict[str, Any]
    centroid: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class GebiedenListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    gebieden: List[GebiedBase]


# ============================================================================
# Indicatoren
# ============================================================================

class IndicatorBase(BaseModel):
    uuid: UUID  # ook uuid5: afgeleide indicatoren uit use cases (#141)
    naam: str
    code: Optional[str] = None
    omschrijving: Optional[str] = None
    eenheid: Optional[str] = None
    categorie: Optional[str] = None


class IndicatorResponse(IndicatorBase):
    aantal_metingen: Optional[int] = 0
    aantal_gebieden_met_data: Optional[int] = None
    coverage_percentage: Optional[float] = None
    nieuwste_jaar: Optional[int] = None
    
    class Config:
        from_attributes = True


class IndicatorenListResponse(BaseModel):
    indicatoren: List[IndicatorResponse]


# ============================================================================
# Indicator Waarden (voor gebied details)
# ============================================================================

class IndicatorWaardeResponse(BaseModel):
    uuid: UUID  # ook uuid5: afgeleide indicatoren uit use cases (#141)
    naam: str
    code: Optional[str] = None
    waarde: float
    jaar: Optional[int] = None
    datum: Optional[datetime] = None
    eenheid: Optional[str] = None
    bron: Optional[str] = None
    
    class Config:
        from_attributes = True


class GebiedDetailResponse(BaseModel):
    gebied: GebiedDetail
    indicatoren: List[IndicatorWaardeResponse]


# ============================================================================
# GeoJSON Responses
# ============================================================================

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: List[Any]  # Nested structure, depends on geometry type


class GeoJSONProperties(BaseModel):
    id: str
    naam: str
    gebiedstype_naam: Optional[str] = None
    indicator_waarde: Optional[float] = None
    indicator_naam: Optional[str] = None
    indicator_code: Optional[str] = None
    eenheid: Optional[str] = None
    jaar: Optional[int] = None
    color: Optional[str] = None  # Backend-calculated hex color for map
    heeft_data: bool = True


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: str
    geometry: Dict[str, Any]  # GeoJSON geometry object
    properties: GeoJSONProperties


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
    metadata: Optional[Dict[str, Any]] = None  # Extra info like count, bounds, etc.


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
