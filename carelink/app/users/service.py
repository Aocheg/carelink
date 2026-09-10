from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


def create_user(
    db: Session,
    username: str,
    full_name: str,
    role: str,
):
    user = User(
        username=username,
        password_hash="NOT_SET_YET",
        full_name=full_name,
        role=role,
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