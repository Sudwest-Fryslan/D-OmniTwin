"""
GET /api/oidc/ik: wie ben ik volgens het token? (#205)

Testendpoint voor de OIDC-koppeling: een ETL of beheerder controleert hiermee of het token
van Keycloak door de backend wordt geaccepteerd en welke rollen meetellen. Alleen met een
geldig token. Geeft geen persoonsgegevens terug (geen `sub`, naam of e-mail), alleen de
client en de rollen.

Staat in een eigen router omdat de laad-API (/api/laden/v1) nog niet bestaat; daar komt
later `GET /api/laden/v1/ik` met dezelfde inhoud.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from omnitwin.oidc import Principal, vereis_principal

router = APIRouter(prefix="/api/oidc", tags=["OIDC"])


class Ik(BaseModel):
    client_id: str | None
    rollen: list[str]


@router.get("/ik", response_model=Ik)
def ik(principal: Principal = Depends(vereis_principal)) -> Ik:
    return Ik(client_id=principal.client_id, rollen=sorted(principal.rollen))
