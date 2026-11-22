from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.clinical.alerts import calculate_news2_score
from app.patients.models import Patient
from app.vitals.models import VitalSign


def _format_utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def export_patient_fhir_bundle(
    db: Session,
    patient_id: int,
    requesting_user_id: int | None = None,
) -> dict[str, Any]:
    """
    Serializes a CareLink patient record, admissions, and vitals into a standardized
    HL7 FHIR Release 4 Collection Bundle with international LOINC and UCUM terminologies.
    """
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise ValueError(f"Patient with ID {patient_id} not found")

    entries: list[dict[str, Any]] = []

    # 1. HL7 FHIR R4 Patient Resource
    sex_str = (patient.sex or "").upper()
    fhir_gender = "male" if sex_str == "MALE" else ("female" if sex_str == "FEMALE" else "other")

    name_parts = (patient.full_name or "").strip().split()
    family_name = name_parts[-1] if len(name_parts) > 1 else (name_parts[0] if name_parts else "")
    given_names = name_parts[:-1] if len(name_parts) > 1 else ([name_parts[0]] if name_parts else [])

    patient_resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [
            {
                "use": "official",
                "system": "http://carelink.health/identifiers/patient-number",
                "value": patient.patient_number,
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.full_name,
                "family": family_name,
                "given": given_names,
            }
        ],
        "gender": fhir_gender,
    }
    if patient.date_of_birth:
        patient_resource["birthDate"] = patient.date_of_birth.isoformat()
    if patient.phone_number:
        patient_resource["telecom"] = [
            {"system": "phone", "value": patient.phone_number, "use": "mobile"}
        ]
    if patient.address:
        patient_resource["address"] = [{"use": "home", "text": patient.address}]

    entries.append({
        "fullUrl": f"urn:uuid:patient-{patient.id}",
        "resource": patient_resource,
    })

    # 2. Query Admissions & Build FHIR Encounter Resources
    adm_stmt = select(Admission).where(Admission.patient_id == patient_id).order_by(Admission.admitted_at.asc())
    admissions = list(db.execute(adm_stmt).scalars().all())
    admission_ids = [adm.id for adm in admissions]

    for adm in admissions:
        encounter_status = "finished" if adm.status == "DISCHARGED" else ("in-progress" if adm.status == "ACTIVE" else "planned")
        period: dict[str, Any] = {"start": _format_utc_iso(adm.admitted_at)}
        if adm.discharged_at:
            period["end"] = _format_utc_iso(adm.discharged_at)

        encounter_resource: dict[str, Any] = {
            "resourceType": "Encounter",
            "id": f"admission-{adm.id}",
            "identifier": [
                {
                    "system": "http://carelink.health/identifiers/admission-number",
                    "value": adm.admission_number,
                }
            ],
            "status": encounter_status,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "IMP",
                "display": "inpatient encounter",
            },
            "subject": {"reference": f"Patient/{patient.id}"},
            "period": period,
        }
        if adm.reason_for_admission:
            encounter_resource["reasonCode"] = [{"text": adm.reason_for_admission}]

        entries.append({
            "fullUrl": f"urn:uuid:encounter-{adm.id}",
            "resource": encounter_resource,
        })

    # 3. Query Vital Signs & Build FHIR Observations with LOINC / UCUM
    if admission_ids:
        vit_stmt = select(VitalSign).where(VitalSign.admission_id.in_(admission_ids)).order_by(VitalSign.recorded_at.asc())
        vitals = list(db.execute(vit_stmt).scalars().all())

        for v in vitals:
            effective_time = _format_utc_iso(v.recorded_at)
            components: list[dict[str, Any]] = []

            # Systolic Blood Pressure (LOINC 8480-6)
            if v.systolic_bp is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(v.systolic_bp),
                        "unit": "mm[Hg]",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                })

            # Diastolic Blood Pressure (LOINC 8462-4)
            if v.diastolic_bp is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(v.diastolic_bp),
                        "unit": "mm[Hg]",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                })

            # Heart Rate (LOINC 8867-4)
            pulse_val = getattr(v, "pulse", None) if getattr(v, "pulse", None) is not None else getattr(v, "heart_rate", None)
            if pulse_val is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8867-4",
                            "display": "Heart rate",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(pulse_val),
                        "unit": "{beats}/min",
                        "system": "http://unitsofmeasure.org",
                        "code": "{beats}/min",
                    },
                })

            # Respiratory Rate (LOINC 9279-1)
            if v.respiratory_rate is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "9279-1",
                            "display": "Respiratory rate",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(v.respiratory_rate),
                        "unit": "{breaths}/min",
                        "system": "http://unitsofmeasure.org",
                        "code": "{breaths}/min",
                    },
                })

            # Body Temperature (LOINC 8310-5)
            if v.temperature is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8310-5",
                            "display": "Body temperature",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(v.temperature),
                        "unit": "Cel",
                        "system": "http://unitsofmeasure.org",
                        "code": "Cel",
                    },
                })

            # Oxygen Saturation SpO2 (LOINC 2708-6)
            spo2_val = getattr(v, "spo2", None) if getattr(v, "spo2", None) is not None else getattr(v, "oxygen_saturation", None)
            if spo2_val is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "2708-6",
                            "display": "Oxygen saturation in Arterial blood",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(spo2_val),
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%",
                    },
                })

            # Calculated NEWS2 Score (LOINC 86488-8)
            news2_val = getattr(v, "news2_score", None)
            if news2_val is None:
                news2_val = calculate_news2_score(v)
            if news2_val is not None:
                components.append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "86488-8",
                            "display": "National Early Warning Score (NEWS2)",
                        }]
                    },
                    "valueQuantity": {
                        "value": float(news2_val),
                        "unit": "{score}",
                        "system": "http://unitsofmeasure.org",
                        "code": "{score}",
                    },
                })

            obs_resource: dict[str, Any] = {
                "resourceType": "Observation",
                "id": f"vitals-{v.id}",
                "status": "final",
                "category": [
                    {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }]
                    }
                ],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional",
                    }]
                },
                "subject": {"reference": f"Patient/{patient.id}"},
                "encounter": {"reference": f"Encounter/admission-{v.admission_id}"},
                "effectiveDateTime": effective_time,
                "component": components,
            }

            entries.append({
                "fullUrl": f"urn:uuid:observation-vitals-{v.id}",
                "resource": obs_resource,
            })

    # Log the export action to the cryptographic audit trail
    create_audit_log(
        db=db,
        user_id=requesting_user_id,
        action="EXPORT_FHIR",
        entity_type="PATIENT",
        entity_id=patient_id,
        details=f"Exported HL7 FHIR R4 Bundle with {len(entries)} resources",
    )

    return {
        "resourceType": "Bundle",
        "id": f"carelink-patient-{patient.id}-fhir-bundle",
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
    }
