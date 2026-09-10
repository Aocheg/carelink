from pydantic import BaseModel


class WardCreate(BaseModel):
    facility_id: int
    name: str
    description: str | None = None


class WardResponse(BaseModel):
    id: int
    facility_id: int
    name: str
    description: str | None
    is_active: bool


class BedCreate(BaseModel):
    ward_id: int
    bed_number: str


class BedResponse(BaseModel):
    id: int
    ward_id: int
    bed_number: str
    status: str