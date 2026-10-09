import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.patients.models import Patient, NextOfKin
from app.facilities.models import Facility
from app.wards.models import Ward, Bed
from app.users.models import User
from app.admissions.models import Admission
from app.audit.models import AuditLog
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db as conn_get_db
from app.users.routes import get_db as users_get_db
from app.medications.routes import get_db as medications_get_db
from app.admissions.routes import get_db as admissions_get_db
from app.patients.routes import get_db as patients_get_db
from app.facilities.routes import get_db as facilities_get_db
from app.wards.routes import get_db as wards_get_db
from app.vitals.routes import get_db as vitals_get_db
from app.investigations.routes import get_db as investigations_get_db
from app.clinical.routes import get_db as clinical_get_db
from app.audit.routes import get_db as audit_get_db

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[conn_get_db] = override_get_db
    app.dependency_overrides[users_get_db] = override_get_db
    app.dependency_overrides[medications_get_db] = override_get_db
    app.dependency_overrides[admissions_get_db] = override_get_db
    app.dependency_overrides[patients_get_db] = override_get_db
    app.dependency_overrides[facilities_get_db] = override_get_db
    app.dependency_overrides[wards_get_db] = override_get_db
    app.dependency_overrides[vitals_get_db] = override_get_db
    app.dependency_overrides[investigations_get_db] = override_get_db
    app.dependency_overrides[clinical_get_db] = override_get_db
    app.dependency_overrides[audit_get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
