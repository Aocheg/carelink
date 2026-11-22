# CARELINK

> **Clinical Continuity, Hospital Workflow & Patient Safety Platform**  
> A production-grade, tested healthcare backend built with Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, and Pydantic v2.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)]()
[![CI](https://github.com/Aocheg/carelink/actions/workflows/ci.yml/badge.svg)](https://github.com/Aocheg/carelink/actions)
[![Tests](https://img.shields.io/badge/Tests-161%20Passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

---

## 1. Clinical Context & Project Vision.

In inpatient hospital practice, communication failures and fragmented medical records during handovers and shift changes remain leading contributors to preventable patient deterioration. 

**CARELINK** is engineered to address these clinical continuity challenges through a reliable, modular, and role-governed healthcare platform. It provides healthcare workers with:
- **Zero-Trust Role-Based Access Control (RBAC)**: Enforcing strict clinical boundaries so only doctors can prescribe or discharge, only clinical staff can record vitals and nursing assessments, and only laboratory personnel can validate diagnostic results.
- **Deterministic National Early Warning Score (NEWS2)**: Real-time physiological score calculation and red-flag clinical alerts (severe hypotension, hypertensive crises, hypothermia, sepsis-risk fever, critical hypoxia, tachy/bradycardia).
- **Shift Handover Summaries**: Single-call aggregated clinical snapshots delivering demographics, allergies, active medications, latest observations, NEWS2 scores, pending tests, and latest doctor/nursing reviews.
- **Unified Chronological Timeline**: An immutable chronological audit stream tracking all patient events from admission to discharge.
- **Bed Management & Discharge Lifecycle**: Automatic bed state tracking (`AVAILABLE` $\leftrightarrow$ `OCCUPIED`), duplicate active admission prevention, and clinical discharge summaries.
- **HL7® FHIR® R4 Interoperability**: Standardized `GET /clinical/fhir/{patient_id}` endpoint exporting patient demographics, hospital encounters, and physiological observations coded in official LOINC and UCUM terminologies.
- **Comprehensive Audit Trail**: Immutable logging across every administrative and clinical transaction.

---

## 2. Architecture & Design Principles.

CARELINK follows a **strict layered architecture** ensuring high cohesion and low coupling:

```
┌────────────────────────────────────────────────────────┐
│                   HTTP Request                         │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│   API Routers (app/*/routes.py)                        │
│   • Input parsing, status codes, response models       │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│   Authentication & RBAC (app/users/dependencies.py)    │
│   • JWT validation, user state check (active/inactive) │
│   • Database-enforced role verification                │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│   Services & Schemas (app/*/service.py & schemas.py)   │
│   • Clinical business rules, Pydantic validation       │
│   • NEWS2 scoring, atomic transaction management       │
│   • Audit log generation                               │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│   Persistence Layer (app/*/models.py & connection.py)  │
│   • SQLAlchemy 2.0 ORM, foreign key relationships      │
│   • SQLite / PostgreSQL database engine                │
└────────────────────────────────────────────────────────┘
```

### Key Design Tenets:
1. **Server-Enforced Role Verification**: The API never trusts a role supplied in headers or client payloads. Role privileges are strictly loaded from authenticated database user records.
2. **Transaction Atomicity**: Multi-entity operations (e.g. admission + bed status update + audit log) are wrapped in atomic database transactions with automatic rollback on error.
3. **Clinical Immutability**: Historical vital signs and clinical notes preserve time-series data without overwriting prior records.

---

## 3. Supported Clinical Roles & Permissions.

CareLink enforces a Zero-Trust Clinical Privilege Model aligned with hospital governance and statutory healthcare councils (MDCN, NMCN, PCN, MLSCN). Roles distinguish between direct clinical authoring/prescribing and vital read/audit access:

| Role | Prescribe Meds | Record Vitals | Doctor Review | Nursing Notes | Lab Results | Discharge | View Audit Logs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ADMIN`** | Yes *(Manage)* | Yes | Yes | Yes | Yes | Yes | **Yes** |
| **`DOCTOR`** | **Yes** *(Prescribe & View)* | **Yes** *(Record & View)* | **Yes** *(Record & View)* | **Yes** *(View & Chart)* | **Yes** *(Order & View)* | **Yes** *(Authorize)* | No |
| **`NURSE`** | **View** *(eMAR Administer)* | **Yes** *(Record & View)* | **View** *(Review Plans)* | **Yes** *(Chart & Notes)* | **View** *(Monitor Results)* | **View** *(Care Summary)* | No |
| **`PHARMACIST`** | **View** *(Reconcile/Dispense)* | **View** *(Dosage Safety)* | **View** *(Clinical Rationale)* | **View** *(Med Monitoring)* | **View** *(Renal/Hepatic)* | **View** *(Discharge Meds)* | No |
| **`LABORATORY_STAFF`** | No | **View** *(Baseline Correlation)*| **View** *(Clinical Indication)* | No | **Yes** *(Record & Flag)* | No | No |

---

## 4. Key Clinical Modules & Hospital Wards Coverage

### 🏥 Hospital-Wide Ward, Specialist Unit & Clinic Coverage
CareLink models the full spectrum of inpatient services and clinical departments across tertiary and general hospitals:
- **Inpatient Medical & Surgical**: Medical Ward (Male/Female Medical Wards), Surgical Ward (Pre/Post-Operative), Orthopedic & Trauma Ward.
- **Critical Care & Emergency**: Intensive Care Unit (ICU), Cardiology & Coronary Care Unit (CCU), Accident & Emergency (A&E) Resuscitation Bay.
- **Maternal, Neonatal & Pediatric**: Pediatric & Children's Emergency Ward (CHER), Special Care Baby Unit (SCBU) / NICU, Maternity & Obstetrics/Gynecology (O&G) Labor Ward.
- **Specialty Units & Outpatient Clinics**: Eye Clinic & Ophthalmology Ward, Nephrology & Dialysis Unit, Oncology & Chemotherapy Unit, Psychiatric & Behavioral Health Ward, General Outpatient Department (GOPD) Observation Bays, Ear Nose & Throat (ENT) Clinic, Dental & Maxillofacial Day Unit.
- Multi-ward and bed occupancy tracking (`app/wards/`).
- Prevents concurrent active admissions for the same patient across all wards.
- Automatically transitions assigned bed status to `OCCUPIED` on admission and frees it back to `AVAILABLE` on discharge.

### 🩺 Vital Signs & NEWS2 Early Warning System
- Time-series observation tracking: Systolic/Diastolic BP, Heart Rate, Respiratory Rate, Temperature, SpO2 (`app/vitals/`).
- Deterministic calculation of **National Early Warning Score (NEWS2)** (`app/clinical/alerts.py`).
- Automated threshold red-flags:
  - Systolic BP $< 90$ mmHg (circulatory shock risk) or $\ge 180$ mmHg (hypertensive crisis)
  - Oxygen saturation $< 88\%$ (critical hypoxia) or $< 92\%$ (hypoxia)
  - Heart rate $< 45$ bpm (severe bradycardia) or $> 130$ bpm (severe tachycardia)
  - Temperature $< 35.0^\circ\text{C}$ (hypothermia) or $\ge 38.5^\circ\text{C}$ (fever/sepsis risk)

### 💊 Medication Orders & Administration
- Complete prescription lifecycle (`app/medications/`): Dose, Route, Frequency, Prescriber, Indications.
- Administration status logging: `ADMINISTERED`, `REFUSED`, `HELD`, `NOT_ADMINISTERED`.
- Doctor-authorized discontinuation with documented clinical rationale.

### 🔬 Diagnostic Investigations
- Test ordering (`ROUTINE`, `URGENT`, `STAT`) by authorized medical staff (`app/investigations/`).
- Result recording with normal reference ranges, abnormal flags, and critical panic value alerts.
- Querying for late/overdue investigation orders (`GET /investigations/late`).

### 📝 Clinical Coordination & Shift Handover
- Comprehensive clinical notes: `DOCTOR_REVIEW`, `NURSING_ASSESSMENT`, `NURSING_DIAGNOSIS`, `NURSING_NOTE`, `HANDOVER_NOTE`.
- Structured shift handover summary endpoint (`GET /clinical/handover/{admission_id}`).
- Unified chronological clinical timeline (`GET /clinical/timeline/{admission_id}`).

### 🔒 Enterprise Tamper-Evident Chained Audit Trail
- System-wide audit logging for every major action: `CREATE`, `ORDER`, `RESULT`, `DISCONTINUE`, `DISCHARGE`.
- **SHA-256 Cryptographic Hash Chaining**: Each audit row stores the `previous_hash` and generates an immutable `current_hash` over the timestamp, user ID, action, and payload, preventing retroactive database tampering.
- **Forensic Verification Endpoint (`GET /audit/verify`)**: Cryptographically validates the entire ledger from Genesis block to latest entry, detecting broken chains or altered records in compliance with **NDPA 2023** and **HIPAA Security Rule**.
- Restricted admin query and forensic endpoints (`GET /audit/` and `GET /audit/verify`).

---

## 5. Getting Started & Installation

You can run CARELINK either using **Docker & Docker Compose** (recommended for full PostgreSQL stack) or directly via a **Python Virtual Environment**.

### Option A: One-Command Docker Compose (Recommended)

Start the entire environment with **PostgreSQL 16**, automatic migrations, and optional fictional demo data:

```bash
git clone https://github.com/Aocheg/carelink.git
cd carelink
docker compose up --build
```

The application will be live at:
- **Service API**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **PostgreSQL Database**: Port `5432` (`carelink_db`)

To stop the containers:
```bash
docker compose down
```

---

### Option B: Local Python Virtual Environment

#### Prerequisites
- **Python 3.12+**
- **Git**

#### Step 1: Clone the Repository
```bash
git clone https://github.com/Aocheg/carelink.git
cd carelink/carelink
```

#### Step 2: Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables
Copy the example environment configuration:
```bash
cp .env.example .env
```
Default configuration (`.env`):
```ini
JWT_SECRET_KEY=carelink-development-secret-key-32bytes-secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./carelink.db
```

#### Step 5: Run Database Migrations
Initialize database tables with Alembic:
```bash
alembic upgrade head
```

#### Step 6: Seed Fictional Demo Data (Optional)
Populate the database with fictional healthcare staff, facilities, wards, patients, and clinical records:
```bash
python -m app.database.seed
```

#### Step 7: Launch the Application
Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- **Service API**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 6. Pre-Configured Fictional Demo Accounts

The seeder (`seed.py`) provisions the following fictional accounts for interactive testing:

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `admin` | `AdminPassword123!` | `ADMIN` | System administrator with full clinical & audit access |
| `dr.adams` | `DoctorPassword123!` | `DOCTOR` | Attending physician (admit, prescribe, review, discharge) |
| `nurse.baker` | `NursePassword123!` | `NURSE` | Ward nurse (record vitals, administer meds, nursing notes) |
| `pharm.clark` | `PharmPassword123!` | `PHARMACIST` | Hospital pharmacist |
| `lab.davis` | `LabPassword123!` | `LABORATORY_STAFF` | Medical laboratory scientist (record test results) |

---

## 7. API Quickstart Examples (cURL)

### 1. Authenticate Staff Member
```bash
curl -X POST "http://127.0.0.1:8000/users/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "dr.adams", "password": "DoctorPassword123!"}'
```
*Response returns JWT Bearer access token.*

### 2. Verify Authenticated User
```bash
curl -X GET "http://127.0.0.1:8000/users/me" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### 3. Generate Clinical Handover Summary
```bash
curl -X GET "http://127.0.0.1:8000/clinical/handover/1"
```

### 4. Fetch Unified Chronological Patient Timeline
```bash
curl -X GET "http://127.0.0.1:8000/clinical/timeline/1"
```

### 5. Evaluate Clinical Early Warning Alerts
```bash
curl -X GET "http://127.0.0.1:8000/clinical/alerts/1"
```

### 6. Discharge Patient & Free Bed (Doctor Only)
```bash
curl -X POST "http://127.0.0.1:8000/admissions/1/discharge" \
  -H "Content-Type: application/json" \
  -d '{
    "discharged_by": 2,
    "discharge_summary": "Pneumonia fully resolved. Vital signs stable. Discharged with 5-day oral course."
  }'
```

---

## 8. Running Tests & Quality Verification

CARELINK includes a comprehensive automated test suite consisting of **161 tests** spanning unit, security, RBAC, database integrity, tamper-evident SHA-256 audit chaining, HL7 FHIR R4 interoperability, end-to-end integration workflows, and web dashboard endpoints.

To run the complete test suite:
```bash
pytest
```

To run with verbose test output:
```bash
pytest -v
```

### Test Suite Structure:
- `tests/test_audit_chain.py`: Tamper-evident SHA-256 hash chaining, genesis block initialization, tamper detection, and admin verification endpoints.
- `tests/test_clinical_fhir.py`: HL7 FHIR R4 Collection Bundle export, LOINC/UCUM clinical terminologies, and RBAC authorization.
- `tests/test_patients.py`: Patient demographic validation and duplicate detection.
- `tests/test_admissions.py`: Admission workflows, bed allocation, and constraints.
- `tests/test_vitals.py` & `test_vitals_safety.py`: Observation validation and safety checks.
- `tests/test_medications.py`: Prescription orders and administration logging.
- `tests/test_users_security.py` & `test_users_tokens.py`: PBKDF2 hashing and JWT token handling.
- `tests/test_users_rbac.py`: Role-based permission enforcement and anti-spoofing tests.
- `tests/test_clinical_workflows.py`: Handover summaries, timeline sorting, investigations, and NEWS2 calculation.
- `tests/test_integration_patient_journey.py`: Full patient journey from emergency admission to discharge.
- `tests/test_dashboard.py`: Clinical web dashboard static mount, root route, and healthcheck verification.

### CI/CD Pipeline (GitHub Actions):
The project includes an automated continuous integration pipeline configured at `.github/workflows/ci.yml`:
- **Automated Test Matrix**: Executes all 161 unit, security, and clinical safety tests under Python 3.12.
- **PostgreSQL Live Service Verification**: Spawns a dedicated PostgreSQL 16 container, applies Alembic database migrations from scratch, and validates idempotent demo data seeding.
- **Docker Image Build & Probe**: Builds the container image via Docker Buildx, launches the container, and verifies HTTP 200 health responses from `GET /health`.

---

## 9. Clinical Safety, Regulatory Framework & Nigerian Health Sector Alignment

> [!IMPORTANT]
> **Academic & Portfolio Notice**: CARELINK is an educational software engineering portfolio platform modeled after real-world hospital workflows and clinical governance tenets. While designed with safety guardrails, deterministic clinical scoring algorithms (NEWS2), and role-segregated boundaries, real-world live clinical deployment requires institutional clinical governance and regulatory onboarding.

### Nigerian Healthcare Regulatory Alignment
For deployment and piloting within the Nigerian healthcare ecosystem (Federal Teaching Hospitals, Federal Medical Centres, State Specialist Hospitals, and Private Health Facilities), CareLink is architected to align with:
- **Nigeria Data Protection Act (NDPA 2023)**: Governed by the Nigeria Data Protection Commission (NDPC). Enforces strict data controller/processor principles, lawful processing of sensitive health records, role-based minimization, and encrypted storage.
- **National Health Act (NHAct 2014)**: Section 26 to 29 guarantees patient confidentiality, access to health records, and statutory user consent mechanisms.
- **Statutory Healthcare Professional Councils**:
  - **Medical and Dental Council of Nigeria (MDCN)**: Ethical guidelines governing prescribing rights, patient reviews, and discharge authorizations.
  - **Nursing and Midwifery Council of Nigeria (NMCN)**: Professional nursing process documentation, vital observation charts, and bedside medication administration.
  - **Pharmacy Council of Nigeria (PCN)**: Drug dispensing accountability, prescription audit logs, and pharmacological reconciliation.
  - **Medical Laboratory Science Council of Nigeria (MLSCN)**: Diagnostic verification standards, critical panic-value alerts, and quality control.
- **National Health Insurance Authority (NHIA)**: Interoperability hooks for patient identification, eligibility, and clinical continuity across accredited providers.

---

## 10. License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
