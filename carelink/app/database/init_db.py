from app.database.connection import Base, engine

from app.patients.models import Patient, NextOfKin
from app.facilities.models import Facility
from app.wards.models import Ward, Bed
from app.users.models import User
from app.admissions.models import Admission
from app.audit.models import AuditLog
from app.vitals.models import VitalSign
from app.medications.models import MedicationOrder, MedicationAdministration
from app.investigations.models import InvestigationOrder, InvestigationResult
from app.clinical.models import ClinicalNote


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


print("Database tables recreated successfully.")