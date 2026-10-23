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
from app.facilities.models import Facility
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
        existing_facility = db.query(Facility).first()
        if existing_facility and not drop_existing:
            print("CareLink fictional demo data already present. Skipping seeder.")
            return

        # 1. Facility (Apex Nigerian Tertiary / Teaching Medical Center)
        facility = create_facility(
            db,
            FacilityCreate(
                name="CareLink National Teaching Hospital & Medical Centre",
                description="Apex tertiary healthcare institution providing comprehensive inpatient, specialized surgical, critical care, and outpatient services across Nigeria.",
            ),
        )

        # 2. Comprehensive Hospital Wards, Specialist Units & Clinics
        # Inpatient Medical & Surgical Wards
        med_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Medical Ward",
                description="Adult inpatient medical care (internal medicine, pulmonology, infectious diseases).",
            ),
        )
        surg_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Surgical Ward",
                description="General surgery, pre-operative optimization, and post-operative surgical convalescence.",
            ),
        )
        ortho_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Orthopedic & Trauma Ward",
                description="Musculoskeletal trauma, fracture stabilization, arthroplasty, and spine care.",
            ),
        )

        # Critical Care & Emergency Units
        icu_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Intensive Care Unit (ICU)",
                description="Multidisciplinary Level-3 critical care, mechanical ventilation, and advanced hemodynamic monitoring.",
            ),
        )
        cardio_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Cardiology & Coronary Care Unit (CCU)",
                description="Acute coronary syndromes, heart failure management, post-catheterization care, and telemetry.",
            ),
        )
        ae_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Accident & Emergency (A&E) Unit",
                description="24/7 acute trauma resuscitation, emergency triage, and clinical stabilization.",
            ),
        )

        # Specialized Medicine & Clinics
        eye_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Eye Clinic & Ophthalmology Ward",
                description="Ophthalmic surgeries (cataract, glaucoma), ocular trauma, and specialized retinal care.",
            ),
        )
        neph_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Nephrology & Dialysis Unit",
                description="Acute kidney injury, hemodialysis suites, and renal replacement therapies.",
            ),
        )
        onc_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Oncology & Chemotherapy Unit",
                description="Cancer staging, chemotherapy infusion, pain management, and palliative support.",
            ),
        )

        # Women & Children's Health
        ped_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Pediatric & Children's Emergency Ward (CHER)",
                description="Pediatric medical/surgical admissions and acute childhood emergencies.",
            ),
        )
        scbu_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Special Care Baby Unit (SCBU) / NICU",
                description="Neonatal intensive care, premature infant incubation, and phototherapy.",
            ),
        )
        mat_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Maternity & Obstetrics/Gynecology (O&G) Ward",
                description="Antenatal care, labor suites, post-caesarean monitoring, and gynecological admissions.",
            ),
        )

        # Outpatient & Behavioral Health Units
        psych_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Psychiatric & Behavioral Health Unit",
                description="Inpatient mental health stabilization, acute neuropsychiatric crisis support, and counseling.",
            ),
        )
        gopd_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="General Outpatient Department (GOPD)",
                description="Primary triage, outpatient consultations, and short-stay clinical observation bays.",
            ),
        )
        ent_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Ear, Nose & Throat (ENT) Clinic & Day Ward",
                description="Head and neck surgical day cases, airway emergencies, and audiology.",
            ),
        )
        dental_ward = create_ward(
            db,
            WardCreate(
                facility_id=facility.id,
                name="Dental & Maxillofacial Unit",
                description="Oral and maxillofacial surgery, dental restorations, and facial trauma stabilization.",
            ),
        )

        # Bed Allocations across Hospital Wards
        bed_med_1 = create_bed(db, BedCreate(ward_id=med_ward.id, bed_number="MED-01"))
        create_bed(db, BedCreate(ward_id=med_ward.id, bed_number="MED-02"))
        create_bed(db, BedCreate(ward_id=med_ward.id, bed_number="MED-03"))
        create_bed(db, BedCreate(ward_id=med_ward.id, bed_number="MED-04"))

        create_bed(db, BedCreate(ward_id=surg_ward.id, bed_number="SURG-101"))
        create_bed(db, BedCreate(ward_id=surg_ward.id, bed_number="SURG-102"))
        create_bed(db, BedCreate(ward_id=surg_ward.id, bed_number="SURG-103"))

        create_bed(db, BedCreate(ward_id=ortho_ward.id, bed_number="ORTHO-01"))
        create_bed(db, BedCreate(ward_id=ortho_ward.id, bed_number="ORTHO-02"))

        create_bed(db, BedCreate(ward_id=icu_ward.id, bed_number="ICU-01"))
        create_bed(db, BedCreate(ward_id=icu_ward.id, bed_number="ICU-02"))
        create_bed(db, BedCreate(ward_id=icu_ward.id, bed_number="ICU-RESUS"))

        create_bed(db, BedCreate(ward_id=cardio_ward.id, bed_number="CARD-01"))
        create_bed(db, BedCreate(ward_id=cardio_ward.id, bed_number="CARD-02"))

        create_bed(db, BedCreate(ward_id=eye_ward.id, bed_number="EYE-01"))
        create_bed(db, BedCreate(ward_id=eye_ward.id, bed_number="EYE-02"))

        create_bed(db, BedCreate(ward_id=ae_ward.id, bed_number="AE-01"))
        create_bed(db, BedCreate(ward_id=ae_ward.id, bed_number="AE-02"))

        create_bed(db, BedCreate(ward_id=ped_ward.id, bed_number="PED-01"))
        create_bed(db, BedCreate(ward_id=ped_ward.id, bed_number="PED-02"))

        create_bed(db, BedCreate(ward_id=mat_ward.id, bed_number="MAT-01"))
        create_bed(db, BedCreate(ward_id=mat_ward.id, bed_number="LABOR-01"))

        create_bed(db, BedCreate(ward_id=scbu_ward.id, bed_number="SCBU-01"))
        create_bed(db, BedCreate(ward_id=neph_ward.id, bed_number="DIALYSIS-01"))
        create_bed(db, BedCreate(ward_id=onc_ward.id, bed_number="ONC-01"))
        create_bed(db, BedCreate(ward_id=psych_ward.id, bed_number="PSYCH-01"))
        create_bed(db, BedCreate(ward_id=gopd_ward.id, bed_number="GOPD-OBS-01"))
        create_bed(db, BedCreate(ward_id=ent_ward.id, bed_number="ENT-01"))
        create_bed(db, BedCreate(ward_id=dental_ward.id, bed_number="DENT-01"))

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

        # 4. Fictional Patients (Contextualized for Nigerian Healthcare Practice)
        patient1 = create_patient(
            db,
            PatientCreate(
                full_name="Eleanor Vance",
                date_of_birth="1985-04-12",
                sex="Female",
                marital_status="Married",
                religion="Christianity",
                occupation="Civil Engineer",
                address="Plot 42 Meadow Lane, Victoria Island, Lagos",
                phone_number="08031234567",
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
                occupation="Retired Principal",
                address="108 Oakwood Avenue, Bodija, Ibadan",
                phone_number="08027654321",
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
                ward_id=med_ward.id,
                bed_id=bed_med_1.id,
                source="Accident & Emergency (A&E)",
                reason_for_admission="Community-acquired pneumonia with fever and dyspnea",
                presenting_complaint="Productive cough with purulent sputum, pleuritic chest pain for 4 days",
                patient_account="NHIA Enrollee #NHIA-88219",
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
        print(f"  Admission: {admission.admission_number} in {med_ward.name}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
