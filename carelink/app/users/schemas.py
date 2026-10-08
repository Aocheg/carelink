from pydantic import BaseModel, field_validator
from app.users.roles import validate_role


class UserCreate(BaseModel):
    username: str
    full_name: str
    role: str
    password: str

    @field_validator("role")
    @classmethod
    def validate_user_role(cls, value: str) -> str:
        return validate_role(value)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

class UserLogin(BaseModel):
    username: str
    password: str
