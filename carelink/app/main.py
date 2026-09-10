from fastapi import FastAPI
from app.patients.routes import router as patient_router
from app.facilities.routes import router as facility_router
from app.wards.routes import router as ward_router

app = FastAPI(
    title="CARELINK",
    description="Clinical Care Coorperation Platform",
    version="0.1.0",
)

app.include_router(patient_router)

app.include_router(facility_router)
app.include_router(ward_router)

@app.get("/health")
def health_check():
    return{
        "status": "healthy",
        "service": "CARELINK",
        "version": "0.1.0",
    }