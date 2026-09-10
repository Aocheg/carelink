from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool