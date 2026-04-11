from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class SystemPromptBase(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    prompt_text: str
    is_actief: bool = True

class SystemPromptCreate(SystemPromptBase):
    pass

class SystemPromptUpdate(BaseModel):
    naam: Optional[str] = None
    beschrijving: Optional[str] = None
    prompt_text: Optional[str] = None
    is_actief: Optional[bool] = None

class SystemPromptResponse(SystemPromptBase):
    id: UUID
    aangemaakt_op: datetime
    laatst_gewijzigd: datetime

    class Config:
        from_attributes = True
