from fastapi import FastAPI

app = FastAPI(
    title="CARELINK",
    description="Clinical Care Coorperation Platform",
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return{
        "status": "healthy",
        "service": "CARELINK",
        "version": "0.1.0",
    }