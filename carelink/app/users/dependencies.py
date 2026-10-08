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


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory to enforce Role-Based Access Control (RBAC).
    
    Verifies that the authenticated user possesses one of the allowed roles.
    Crucially, the user's role is retrieved from the database record via
    get_current_user, ensuring the API NEVER trusts a role supplied directly
    by client headers, query parameters, or request payload.
    """
    # Flatten any nested lists/tuples and normalize to uppercase strings
    flattened: list[str] = []
    for r in allowed_roles:
        if isinstance(r, (list, set, tuple)):
            flattened.extend(r)
        else:
            flattened.append(r)
    normalized_allowed = {str(item).strip().upper() for item in flattened}

    def role_verifier(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = (current_user.role or "").strip().upper()
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=403,
                detail="Operation not permitted for this user role",
            )
        return current_user

    return role_verifier


def require_permission(permission: str):
    """
    FastAPI dependency factory to enforce granular permissions based on user role.
    """
    from app.users.roles import has_permission

    def permission_verifier(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' denied for role '{current_user.role}'",
            )
        return current_user

    return permission_verifier