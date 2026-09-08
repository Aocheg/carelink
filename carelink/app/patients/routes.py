from fastapi import APIRouter

from app.patients.schemas import PatientCreate

# Creating a group of patient related endpoint
router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.post("/")
def create_patient(patient: PatientCreate):
    return {
        "message": "Patient data received successfully",
        "patient": patient
    }
