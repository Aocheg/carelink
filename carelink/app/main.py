from fastapi import FastAPI

from app.database.connection import Base, engine

# Import models so SQLAlchemy knows about every table
# before create_all() runs.
from app.patients.models import Patient, NextOfKin
from app.facilities.models import Facility
from app.wards.models import Ward, Bed
from app.users.models import User
from app.admissions.models import Admission
from app.audit.models import AuditLog
from app.vitals.models import VitalSign
from app.medications.models import MedicationOrder

from app.patients.routes import router as patients_router
from app.facilities.routes import router as facilities_router
from app.wards.routes import router as wards_router
from app.users.routes import router as users_router
from app.admissions.routes import router as admissions_router
from app.vitals.routes import router as vitals_router
from app.medications.routes import router as medications_router


# Create database tables that do not already exist.
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="CARELINK",
    description=(
        "Clinical Continuity & Care Coordination Platform "
        "for healthcare workflow and patient safety."
    ),
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CARELINK",
        "version": "0.1.0",
    }


app.include_router(patients_router)
app.include_router(facilities_router)
app.include_router(wards_router)
app.include_router(users_router)
app.include_router(admissions_router)
app.include_router(vitals_router)
app.include_router(medications_router)