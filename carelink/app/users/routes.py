from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.users.schemas import UserCreate, UserResponse
from app.users.service import (
    create_user,
    get_users,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201
)
def create_user_endpoint(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    return create_user(
        db,
        user.username,
        user.full_name,
        user.role,
    )


@router.get(
    "/",
    response_model=list[UserResponse]
)
def get_users_endpoint(
    db: Session = Depends(get_db)
):
    return get_users(db)