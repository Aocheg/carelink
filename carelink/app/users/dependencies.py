from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.users.tokens import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        ) from exc

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID in access token",
        ) from exc

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is inactive",
        )

    return user