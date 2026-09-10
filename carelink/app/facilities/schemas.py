from pydantic import BaseModel


class FacilityCreate(BaseModel):
    name: str
    description: str | None = None


class FacilityResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool