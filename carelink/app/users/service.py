from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User
from app.users.roles import validate_role
from app.users.security import hash_password, verify_password

def create_user(
    db: Session,
    username: str,
    full_name: str,
    role: str,
    password: str,
):
    normalized_role = validate_role(role)
    password_hash = hash_password(password)

    user = User(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        role=normalized_role,
    )


    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_users(db: Session):
    result = db.execute(
        select(User).order_by(User.id)
    )

    return result.scalars().all()


def get_user_by_id(db: Session, user_id: int):
    result = db.execute(
        select(User).where(User.id == user_id)
    )

    return result.scalar_one_or_none()
def authenticate_user(
    db: Session,
    username: str,
    password: str,
):
    result = db.execute(
        select(User).where(User.username == username)
    )

    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user