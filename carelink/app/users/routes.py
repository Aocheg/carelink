from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.users.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.users.service import (
    authenticate_user,
    create_user,
    get_users,
)
from app.users.dependencies import get_current_user, require_roles
from app.users.models import User
from app.users.tokens import create_access_token


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
        user.password,
    )


@router.get(
    "/",
    response_model=list[UserResponse]
)
def get_users_endpoint(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles("ADMIN")),
):
    return get_users(db)


@router.get(
    "/roles",
)
def get_roles_endpoint():
    from app.users.roles import ROLE_PERMISSIONS, SUPPORTED_ROLES
    return {
        "roles": sorted(SUPPORTED_ROLES),
        "permissions": {k: sorted(v) for k, v in ROLE_PERMISSIONS.items()},
    }



@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ADD THE LOGIN ROUTE HERE

@router.post("/login")
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):
    authenticated_user = authenticate_user(
        db,
        user.username,
        user.password,
    )

    if authenticated_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    access_token = create_access_token(
        user_id=authenticated_user.id,
        username=authenticated_user.username,
        role=authenticated_user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }