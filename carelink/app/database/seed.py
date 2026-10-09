"""
CareLink Fictional Demo Data Seeder
Populates a fresh or existing database with safe, realistic, fictional clinical data.
Strictly adheres to data protection: zero live patient data, fictional names only.
"""

from datetime import date, datetime, timedelta, timezone

from app.admissions.schemas import AdmissionCreate
from app.admissions.service import create_admission
from app.clinical.schemas import ClinicalNoteCreate
from app.clinical.service import create_clinical_note
from app.database.connection import Base, SessionLocal, engine
from app.facilities.schemas import FacilityCreate
from app.facilities.service import create_facility
from app.investigations.schemas import InvestigationOrderCreate, InvestigationResultCreate
from app.investigations.service import create_investigation_order, record_investigation_result
from app.medications.schemas import MedicationAdministrationCreate, MedicationOrderCreate
from app.medications.service import create_medication_administration, create_medication_order
from app.patients.schemas import PatientCreate
from app.patients.service import create_patient
from app.users.service import create_user
from app.vitals.schemas import VitalSignCreate
from app.vitals.service import create_vital_sign
from app.wards.schemas import BedCreate, WardCreate
from app.wards.service import create_bed, create_ward


from sqlalchemy.orm import sessionmaker

def seed_database(target_engine=None, drop_existing: bool = False) -> None:
    used_engine = target_engine or engine
    if drop_existing:
        Base.metadata.drop_all(bind=used_engine)
        Base.metadata.create_all(bind=used_engine)

    Session = sessionmaker(bind=used_engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        # 1. Facility
        facility = create_facility(
            db,
            FacilityCreate(
                name="CareLink Regional Medical Center",
                description="Tertiary teaching hospital with acute medical and surgical services.",
            ),
        )

        # 2. Wards & Beds
        amu_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Acute Medical Unit (AMU)",
                description="Acute assessment and stabilization unit.",
            ),
        )
        surg_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Surgical Ward 3B",
                description="Post-operative inpatient surgical care.",
            ),
        )

        bed_amu_1 = create_bed(db, BedCreate(ward_id=amu_ward.id, bed_number="AMU-01"))
        create_bed(db, BedCreate(ward_id=amu_ward.id, bed_number="AMU-02"))
        create_bed(db, BedCreate(ward_id=amu_ward.id, bed_number="AMU-03"))
        create_bed(db, BedCreate(ward_id=surg_ward.id, bed_number="SW-101"))
        create_bed(db, BedCreate(ward_id=surg_ward.id, bed_number="SW-102"))

        # 3. Healthcare Staff Users (Role-Based)
        admin = create_user(
            db,
            username="admin",
            full_name="Hospital Administrator",
            role="ADMIN",
            password="AdminPassword123!",
        )

        doctor = create_user(
            db,
            username="dr.adams",
            full_name="Dr. Sarah Adams, MD",
            role="DOCTOR",
            password="DoctorPassword123!",
        )

        nurse = create_user(
            db,
            username="nurse.baker",
            full_name="Nurse David Baker, RN",
            role="NURSE",
            password="NursePassword123!",
        )

        pharmacist = create_user(
            db,
            username="pharm.clark",
            full_name="Dr. Helen Clark, PharmD",
            role="PHARMACIST",
            password="PharmPassword123!",
        )

        lab_tech = create_user(
            db,
            username="lab.davis",
            full_name="Marcus Davis, MLS",
            role="LABORATORY_STAFF",
            password="LabPassword123!",
        )

        # 4. Fictional Patients
        patient1 = create_patient(
            db,
            PatientCreate(
                full_name="Eleanor Vance",
                date_of_birth="1985-04-12",
                sex="Female",
                marital_status="Married",
                religion="None",
                occupation="Civil Engineer",
                address="42 Meadow Lane, Riverdale",
                phone_number="08012345678",
                blood_group="A+",
                genotype="AA",
                allergy_status="Penicillin",
                allergy_details="Severe urticarial rash and angioedema (2021).",
            ),
        )

        create_patient(
            db,
            PatientCreate(
                full_name="Arthur Pendelton",
                date_of_birth="1952-11-20",
                sex="Male",
                marital_status="Widowed",
                religion="Christianity",
                occupation="Retired Librarian",
                address="108 Oakwood Avenue, Riverdale",
                phone_number="08087654321",
                blood_group="O+",
                genotype="AA",
                allergy_status="No known allergy",
            ),
        )

        # 5. Inpatient Admission
        admission = create_admission(
            db,
            AdmissionCreate(
                patient_id=patient1.id,
                ward_id=amu_ward.id,
                bed_id=bed_amu_1.id,
                source="Emergency Department",
                reason_for_admission="Community-acquired pneumonia with fever and dyspnea",
                presenting_complaint="Productive cough with purulent sputum, pleuritic chest pain for 4 days",
                patient_account="General Healthcare Scheme #GH-88219",
                doctor_assessment="Right lower lobe consolidation on initial chest radiograph. Hemodynamically stable.",
                nursing_assessment="Alert and oriented. Mild accessory muscle use on room air.",
                nursing_diagnosis="Impaired gas exchange related to alveolar consolidation.",
                admitted_by=doctor.id,
            ),
        )

        # 6. Vital Signs Observation Series
        now = datetime.now(timezone.utc)
        create_vital_sign(
            db,
            VitalSignCreate(
                admission_id=admission.id,
                recorded_by=nurse.id,
                recorded_at=now - timedelta(hours=6),
                systolic_bp=105,
                diastolic_bp=68,
                pulse=104,
                temperature=38.6,
                respiratory_rate=22,
                spo2=93.0,
                measurement_status="COMPLETE",
                notes="Patient febrile and tachypneic. Oxygen started at 2L/min via nasal cannula.",
            ),
        )

        create_vital_sign(
            db,
            VitalSignCreate(
                admission_id=admission.id,
                recorded_by=nurse.id,
                recorded_at=now - timedelta(hours=2),
                systolic_bp=118,
                diastolic_bp=74,
                pulse=86,
                temperature=37.3,
                respiratory_rate=18,
                spo2=97.0,
                measurement_status="COMPLETE",
                notes="Fever subsided after antipyretic. Breathing easier.",
            ),
        )

        # 7. Medication Order & Administration
        med_order = create_medication_order(
            db,
            MedicationOrderCreate(
                admission_id=admission.id,
                medication_name="Levofloxacin",
                dose="500mg",
                route="IV",
                frequency="Once daily",
                start_date=date.today(),
                prescribed_by=doctor.id,
                instructions="Infuse in 100mL 0.9% Normal Saline over 60 minutes. Note penicillin allergy.",
            ),
        )

        create_medication_administration(
            db,
            MedicationAdministrationCreate(
                medication_order_id=med_order.id,
                administered_by=nurse.id,
                status="ADMINISTERED",
                notes="Infusion completed smoothly without adverse events.",
            ),
        )

        # 8. Clinical Notes
        create_clinical_note(
            db,
            ClinicalNoteCreate(
                admission_id=admission.id,
                author_id=doctor.id,
                note_type="DOCTOR_REVIEW",
                content="Patient responding well to IV levofloxacin. Oxygen saturation stable on minimal nasal cannula support.",
                plan="Continue IV antibiotics x 48h. Check repeat inflammatory markers tomorrow. Switch to oral when eating well.",
            ),
        )

        create_clinical_note(
            db,
            ClinicalNoteCreate(
                admission_id=admission.id,
                author_id=nurse.id,
                note_type="NURSING_NOTE",
                content="Patient ambulated to bathroom independently with supervision. Appetite improving.",
                plan="Encourage oral fluid intake. Monitor vital signs every 4 hours.",
            ),
        )

        # 9. Investigation Order & Lab Result
        lab_order = create_investigation_order(
            db,
            InvestigationOrderCreate(
                admission_id=admission.id,
                test_name="Full Blood Count (FBC)",
                category="HEMATOLOGY",
                ordered_by=doctor.id,
                urgency="ROUTINE",
                clinical_indication="Baseline infection monitoring for pneumonia",
            ),
        )

        record_investigation_result(
            db,
            InvestigationResultCreate(
                investigation_order_id=lab_order.id,
                recorded_by=lab_tech.id,
                result_value="WBC: 14.2 x10^9/L (Leukocytosis), Hb: 13.5 g/dL, Platelets: 280 x10^9/L",
                reference_range="WBC: 4.0 - 11.0 x10^9/L",
                is_abnormal=True,
                critical_alert=False,
                notes="Elevated white cell count consistent with active bacterial infection.",
            ),
        )

        print("Fictional demo data seeded successfully:")
        print(f"  Facility: {facility.name}")
        print(f"  Users: admin, {doctor.username}, {nurse.username}, {pharmacist.username}, {lab_tech.username}")
        print(f"  Patients: Eleanor Vance ({patient1.patient_number})")
        print(f"  Admission: {admission.admission_number} in {amu_ward.name}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
