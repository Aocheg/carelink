from app.database.connection import Base, engine
from app.patients.models import Patient


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print("Database tables recreated successfully.")