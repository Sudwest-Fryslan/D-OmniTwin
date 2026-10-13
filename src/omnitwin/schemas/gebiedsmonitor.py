# Pydantic Schemas voor Gebiedsmonitor API
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Gebiedstypes
# ============================================================================


class GebiedstypeBase(BaseModel):
    naam: str
    code: str | None = None
    beschrijving: str | None = None
    bron: str | None = None
    niveau: str | None = None


class GebiedstypeResponse(GebiedstypeBase):
    id: UUID
    aantal_gebieden: int | None = 0

    class Config:
        from_attributes = True


class GebiedstypesListResponse(BaseModel):
    gebiedstypes: list[GebiedstypeResponse]


# ============================================================================
# Gebieden
# ============================================================================


class GebiedBase(BaseModel):
    id: str
    naam: str
    gebiedstype_naam: str | None = None
    heeft_data: bool = False
    aantal_indicatoren: int = 0


class GebiedDetail(BaseModel):
    id: str
    naam: str
    gebiedstype: dict[str, Any]
    centroid: dict[str, float] | None = None
    metadata: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class GebiedenListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    gebieden: list[GebiedBase]


# ============================================================================
# Indicatoren
# ============================================================================


class IndicatorBase(BaseModel):
    uuid: UUID  # ook uuid5: afgeleide indicatoren uit use cases (#141)
    naam: str
    code: str | None = None
    omschrijving: str | None = None
    eenheid: str | None = None
    categorie: str | None = None


class IndicatorResponse(IndicatorBase):
    aantal_metingen: int | None = 0
    aantal_gebieden_met_data: int | None = None
    coverage_percentage: float | None = None
    nieuwste_jaar: int | None = None

    class Config:
        from_attributes = True


class IndicatorenListResponse(BaseModel):
    indicatoren: list[IndicatorResponse]


# ============================================================================
# Indicator Waarden (voor gebied details)
# ============================================================================


class IndicatorWaardeResponse(BaseModel):
    uuid: UUID  # ook uuid5: afgeleide indicatoren uit use cases (#141)
    naam: str
    code: str | None = None
    waarde: float
    jaar: int | None = None
    datum: datetime | None = None
    eenheid: str | None = None
    bron: str | None = None

    class Config:
        from_attributes = True


class GebiedDetailResponse(BaseModel):
    gebied: GebiedDetail
    indicatoren: list[IndicatorWaardeResponse]


# ============================================================================
# GeoJSON Responses
# ============================================================================


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: list[Any]  # Nested structure, depends on geometry type


class GeoJSONProperties(BaseModel):
    id: str
    naam: str
    gebiedstype_naam: str | None = None
    indicator_waarde: float | None = None
    indicator_naam: str | None = None
    indicator_code: str | None = None
    eenheid: str | None = None
    jaar: int | None = None
    color: str | None = None  # Backend-calculated hex color for map
    heeft_data: bool = True


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: str
    geometry: dict[str, Any]  # GeoJSON geometry object
    properties: GeoJSONProperties


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
    metadata: dict[str, Any] | None = None  # Extra info like count, bounds, etc.


# ============================================================================
# Error Response
# ============================================================================


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
