from datetime import date, datetime, timezone

from app.admissions.models import Admission
from app.audit.models import AuditLog
from app.facilities.models import Facility
from app.medications.models import (
    MedicationAdministration,
    MedicationOrder,
)
from app.medications.schemas import (
    MedicationAdministrationCreate,
    MedicationOrderCreate,
)
from app.medications.service import (
    create_medication_administration,
    create_medication_order,
    get_medication_administration_by_id,
    get_medication_administrations_by_order,
    get_medication_order_by_id,
    get_medication_orders_by_admission,
)
from app.patients.models import Patient
from app.wards.models import Bed, Ward
from app.users.models import User


def create_test_data(db):
    facility = Facility(
        name="Test Facility",
        description="Facility for medication tests",
    )
    db.add(facility)
    db.flush()

    ward = Ward(
        facility_id=facility.id,
        name="Test Ward",
        description="Ward for medication tests",
    )
    db.add(ward)
    db.flush()

    bed = Bed(
        ward_id=ward.id,
        bed_number="MED-001",
        status="AVAILABLE",
    )
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number="CL-999001",
        full_name="Medication Test Patient",
        date_of_birth=date(1990, 1, 1),
        sex="Male",
        marital_status="Single",
        religion="Christianity",
        occupation="Engineer",
        address="Test Address",
        phone_number="08000000000",
        blood_group="O+",
        genotype="AA",
        allergy_status="NO",
        allergy_details=None,
    )
    db.add(patient)
    db.flush()

    doctor = User(
        username="testdoctor",
        password_hash="NOT_SET_YET",
        full_name="Test Doctor",
        role="DOCTOR",
        is_active=True,
    )
    db.add(doctor)
    db.flush()

    nurse = User(
        username="testnurse",
        password_hash="NOT_SET_YET",
        full_name="Test Nurse",
        role="NURSE",
        is_active=True,
    )
    db.add(nurse)
    db.flush()

    admission = Admission(
        admission_number="ADM-TEST-001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="DOCTOR",
        reason_for_admission="Medication test admission",
        presenting_complaint="Test complaint",
        admitted_by=nurse.id,
        status="ACTIVE",
    )
    db.add(admission)
    db.flush()

    bed.status = "OCCUPIED"

    db.commit()
    db.refresh(admission)

    return admission, doctor, nurse


def create_medication_data(
    admission_id,
    doctor_id,
):
    return MedicationOrderCreate(
        admission_id=admission_id,
        medication_name="Amoxicillin",
        dose="500 mg",
        route="ORAL",
        frequency="TDS",
        start_date=date(2026, 9, 15),
        end_date=date(2026, 9, 20),
        prescribed_by=doctor_id,
        status="ACTIVE",
        instructions="Take after meals",
    )


def create_administration_data(
    medication_order_id,
    nurse_id,
):
    return MedicationAdministrationCreate(
        medication_order_id=medication_order_id,
        administered_by=nurse_id,
        administered_at=datetime(
            2026,
            9,
            15,
            8,
            0,
            tzinfo=timezone.utc,
        ),
        status="ADMINISTERED",
        notes="Medication administered as prescribed",
    )


def test_create_medication_order(db):
    admission, doctor, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        doctor.id,
    )

    medication_order = create_medication_order(
        db,
        medication_data,
    )

    assert medication_order.id is not None
    assert medication_order.admission_id == admission.id
    assert medication_order.medication_name == "Amoxicillin"
    assert medication_order.dose == "500 mg"
    assert medication_order.route == "ORAL"
    assert medication_order.frequency == "TDS"
    assert medication_order.status == "ACTIVE"
    assert medication_order.prescribed_by == doctor.id


def test_create_medication_order_creates_audit_log(db):
    admission, doctor, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        doctor.id,
    )

    medication_order = create_medication_order(
        db,
        medication_data,
    )

    audit_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "MEDICATION_ORDER",
            AuditLog.entity_id == medication_order.id,
        )
        .first()
    )

    assert audit_log is not None
    assert audit_log.action == "CREATE"
    assert audit_log.user_id == doctor.id


def test_create_medication_order_rejects_nonexistent_admission(db):
    _, doctor, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission_id=999999,
        doctor_id=doctor.id,
    )

    try:
        create_medication_order(
            db,
            medication_data,
        )
        assert False
    except ValueError as error:
        assert str(error) == "Admission not found"


def test_create_medication_order_rejects_nonexistent_prescriber(db):
    admission, _, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission_id=admission.id,
        doctor_id=999999,
    )

    try:
        create_medication_order(
            db,
            medication_data,
        )
        assert False
    except ValueError as error:
        assert (
            str(error)
            == "Prescribing healthcare worker not found"
        )


def test_create_medication_order_rejects_inactive_prescriber(db):
    admission, doctor, _ = create_test_data(db)

    doctor.is_active = False
    db.commit()

    medication_data = create_medication_data(
        admission.id,
        doctor.id,
    )

    try:
        create_medication_order(
            db,
            medication_data,
        )
        assert False
    except ValueError as error:
        assert (
            str(error)
            == "Prescribing healthcare worker is inactive"
        )


def test_get_medication_order_by_id(db):
    admission, doctor, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        doctor.id,
    )

    medication_order = create_medication_order(
        db,
        medication_data,
    )

    result = get_medication_order_by_id(
        db,
        medication_order.id,
    )

    assert result is not None
    assert result.id == medication_order.id


def test_get_medication_orders_by_admission(db):
    admission, doctor, _ = create_test_data(db)

    first_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    second_order = create_medication_order(
        db,
        MedicationOrderCreate(
            admission_id=admission.id,
            medication_name="Paracetamol",
            dose="1 g",
            route="ORAL",
            frequency="QID",
            start_date=date(2026, 9, 15),
            end_date=None,
            prescribed_by=doctor.id,
            status="ACTIVE",
            instructions=None,
        ),
    )

    results = get_medication_orders_by_admission(
        db,
        admission.id,
    )

    assert len(results) == 2
    assert results[0].id == first_order.id
    assert results[1].id == second_order.id


def test_get_medication_orders_by_admission_rejects_nonexistent_admission(
    db,
):
    create_test_data(db)

    try:
        get_medication_orders_by_admission(
            db,
            999999,
        )
        assert False
    except ValueError as error:
        assert str(error) == "Admission not found"


def test_create_medication_administration(db):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration_data = create_administration_data(
        medication_order.id,
        nurse.id,
    )

    administration = create_medication_administration(
        db,
        administration_data,
    )

    assert administration.id is not None
    assert (
        administration.medication_order_id
        == medication_order.id
    )
    assert administration.administered_by == nurse.id
    assert (
        administration.administered_at
        == datetime(
            2026,
            9,
            15,
            8,
            0,
            tzinfo=timezone.utc,
        )
    )
    assert administration.status == "ADMINISTERED"


def test_create_medication_administration_creates_audit_log(
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration = create_medication_administration(
        db,
        create_administration_data(
            medication_order.id,
            nurse.id,
        ),
    )

    audit_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type
            == "MEDICATION_ADMINISTRATION",
            AuditLog.entity_id == administration.id,
        )
        .first()
    )

    assert audit_log is not None
    assert audit_log.action == "CREATE"
    assert audit_log.user_id == nurse.id


def test_create_medication_administration_rejects_nonexistent_order(
    db,
):
    _, _, nurse = create_test_data(db)

    administration_data = create_administration_data(
        medication_order_id=999999,
        nurse_id=nurse.id,
    )

    try:
        create_medication_administration(
            db,
            administration_data,
        )
        assert False
    except ValueError as error:
        assert str(error) == "Medication order not found"


def test_create_medication_administration_rejects_nonexistent_user(
    db,
):
    admission, doctor, _ = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration_data = create_administration_data(
        medication_order.id,
        nurse_id=999999,
    )

    try:
        create_medication_administration(
            db,
            administration_data,
        )
        assert False
    except ValueError as error:
        assert (
            str(error)
            == "Administering healthcare worker not found"
        )


def test_create_medication_administration_rejects_inactive_user(
    db,
):
    admission, doctor, nurse = create_test_data(db)

    nurse.is_active = False
    db.commit()

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration_data = create_administration_data(
        medication_order.id,
        nurse.id,
    )

    try:
        create_medication_administration(
            db,
            administration_data,
        )
        assert False
    except ValueError as error:
        assert (
            str(error)
            == "Administering healthcare worker is inactive"
        )


def test_get_medication_administration_by_id(db):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration = create_medication_administration(
        db,
        create_administration_data(
            medication_order.id,
            nurse.id,
        ),
    )

    result = get_medication_administration_by_id(
        db,
        administration.id,
    )

    assert result is not None
    assert result.id == administration.id


def test_get_medication_administrations_by_order(db):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    first_administration = create_medication_administration(
        db,
        create_administration_data(
            medication_order.id,
            nurse.id,
        ),
    )

    second_administration = create_medication_administration(
        db,
        MedicationAdministrationCreate(
            medication_order_id=medication_order.id,
            administered_by=nurse.id,
            administered_at=datetime(
                2026,
                9,
                15,
                14,
                0,
                tzinfo=timezone.utc,
            ),
            status="REFUSED",
            not_administered_reason=(
                "Patient refused medication"
            ),
            notes=None,
        ),
    )

    results = get_medication_administrations_by_order(
        db,
        medication_order.id,
    )

    assert len(results) == 2
    assert results[0].id == first_administration.id
    assert results[1].id == second_administration.id


def test_get_medication_administrations_by_order_rejects_nonexistent_order(
    db,
):
    create_test_data(db)

    try:
        get_medication_administrations_by_order(
            db,
            999999,
        )
        assert False
    except ValueError as error:
        assert str(error) == "Medication order not found"


# ---------------------------------------------------------------------------
# Medication API tests
# ---------------------------------------------------------------------------


def test_api_create_medication_order(client, db):
    admission, doctor, _ = create_test_data(db)

    response = client.post(
        "/medications/",
        json={
            "admission_id": admission.id,
            "medication_name": "Amoxicillin",
            "dose": "500 mg",
            "route": "ORAL",
            "frequency": "TDS",
            "start_date": "2026-09-15",
            "end_date": "2026-09-20",
            "prescribed_by": doctor.id,
            "status": "ACTIVE",
            "instructions": "Take after meals",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["admission_id"] == admission.id
    assert data["medication_name"] == "Amoxicillin"
    assert data["dose"] == "500 mg"
    assert data["route"] == "ORAL"
    assert data["frequency"] == "TDS"
    assert data["status"] == "ACTIVE"
    assert data["prescribed_by"] == doctor.id


def test_api_get_medication_order(client, db):
    admission, doctor, _ = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    response = client.get(
        f"/medications/{medication_order.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == medication_order.id
    assert data["medication_name"] == "Amoxicillin"


def test_api_get_medication_orders_by_admission(
    client,
    db,
):
    admission, doctor, _ = create_test_data(db)

    create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    response = client.get(
        f"/medications/admission/{admission.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["admission_id"] == admission.id
    assert data[0]["medication_name"] == "Amoxicillin"


def test_api_create_medication_administration(
    client,
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    response = client.post(
        "/medications/administrations",
        json={
            "medication_order_id": medication_order.id,
            "administered_by": nurse.id,
            "administered_at": "2026-09-15T08:00:00Z",
            "status": "ADMINISTERED",
            "notes": "Medication administered as prescribed",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert (
        data["medication_order_id"]
        == medication_order.id
    )
    assert data["administered_by"] == nurse.id
    assert data["status"] == "ADMINISTERED"


def test_api_get_medication_administration(
    client,
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    administration = create_medication_administration(
        db,
        create_administration_data(
            medication_order.id,
            nurse.id,
        ),
    )

    response = client.get(
        f"/medications/administrations/{administration.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == administration.id
    assert (
        data["medication_order_id"]
        == medication_order.id
    )
    assert data["status"] == "ADMINISTERED"


def test_api_get_medication_administrations_by_order(
    client,
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    create_medication_administration(
        db,
        create_administration_data(
            medication_order.id,
            nurse.id,
        ),
    )

    response = client.get(
        f"/medications/order/"
        f"{medication_order.id}/administrations",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert (
        data[0]["medication_order_id"]
        == medication_order.id
    )


def test_api_get_nonexistent_medication_order(
    client,
):
    response = client.get(
        "/medications/999999",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Medication order not found"
    )


def test_api_get_nonexistent_medication_administration(
    client,
):
    response = client.get(
        "/medications/administrations/999999",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Medication administration not found"
    )


def test_api_rejects_invalid_medication_order(
    client,
):
    response = client.post(
        "/medications/",
        json={
            "admission_id": 999999,
            "medication_name": "Amoxicillin",
            "dose": "500 mg",
            "route": "ORAL",
            "frequency": "TDS",
            "start_date": "2026-09-15",
            "end_date": "2026-09-20",
            "prescribed_by": 999999,
            "status": "ACTIVE",
            "instructions": "Take after meals",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Admission not found"
    )


def test_api_rejects_medication_administration_without_reason(
    client,
):
    response = client.post(
        "/medications/administrations",
        json={
            "medication_order_id": 1,
            "administered_by": 1,
            "administered_at": "2026-09-15T08:00:00Z",
            "status": "REFUSED",
        },
    )

    assert response.status_code == 422


def test_medication_order_schema_rejects_discontinued_status():
    try:
        MedicationOrderCreate(
            admission_id=1,
            medication_name="Amoxicillin",
            dose="500 mg",
            route="ORAL",
            frequency="TDS",
            start_date=date(2026, 9, 15),
            end_date=None,
            prescribed_by=1,
            status="DISCONTINUED",
            instructions=None,
        )
        assert False
    except ValueError as error:
        assert "must have status ACTIVE" in str(error)


def test_medication_order_schema_rejects_completed_status():
    try:
        MedicationOrderCreate(
            admission_id=1,
            medication_name="Amoxicillin",
            dose="500 mg",
            route="ORAL",
            frequency="TDS",
            start_date=date(2026, 9, 15),
            end_date=None,
            prescribed_by=1,
            status="COMPLETED",
            instructions=None,
        )
        assert False
    except ValueError as error:
        assert "must have status ACTIVE" in str(error)


def test_medication_administration_rejects_discontinued_order(
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    medication_order.status = "DISCONTINUED"
    db.commit()

    administration_data = create_administration_data(
        medication_order.id,
        nurse.id,
    )

    try:
        create_medication_administration(
            db,
            administration_data,
        )
        assert False
    except ValueError as error:
        assert str(error) == (
            "Medication order is not active"
        )


def test_medication_administration_rejects_completed_order(
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    medication_order.status = "COMPLETED"
    db.commit()

    administration_data = create_administration_data(
        medication_order.id,
        nurse.id,
    )

    try:
        create_medication_administration(
            db,
            administration_data,
        )
        assert False
    except ValueError as error:
        assert str(error) == (
            "Medication order is not active"
        )


def test_api_rejects_discontinued_new_medication_order(
    client,
    db,
):
    admission, doctor, _ = create_test_data(db)

    response = client.post(
        "/medications/",
        json={
            "admission_id": admission.id,
            "medication_name": "Amoxicillin",
            "dose": "500 mg",
            "route": "ORAL",
            "frequency": "TDS",
            "start_date": "2026-09-15",
            "end_date": None,
            "prescribed_by": doctor.id,
            "status": "DISCONTINUED",
            "instructions": None,
        },
    )

    assert response.status_code == 422


def test_api_rejects_administration_for_discontinued_order(
    client,
    db,
):
    admission, doctor, nurse = create_test_data(db)

    medication_order = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            doctor.id,
        ),
    )

    medication_order.status = "DISCONTINUED"
    db.commit()

    response = client.post(
        "/medications/administrations",
        json={
            "medication_order_id": medication_order.id,
            "administered_by": nurse.id,
            "administered_at": "2026-09-15T08:00:00Z",
            "status": "ADMINISTERED",
            "notes": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Medication order is not active"
    )