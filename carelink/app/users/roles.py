from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    LABORATORY_STAFF = "LABORATORY_STAFF"
    LAB_TECH = "LAB_TECH"


# Canonical list of supported roles
SUPPORTED_ROLES = {
    Role.ADMIN.value,
    Role.DOCTOR.value,
    Role.NURSE.value,
    Role.PHARMACIST.value,
    Role.LABORATORY_STAFF.value,
    Role.LAB_TECH.value,
}

# Role groupings for high-level clinical access
CLINICAL_STAFF = {
    Role.DOCTOR.value,
    Role.NURSE.value,
    Role.ADMIN.value,
}

PRESCRIBING_STAFF = {
    Role.DOCTOR.value,
    Role.ADMIN.value,
}

ADMINISTERING_STAFF = {
    Role.NURSE.value,
    Role.DOCTOR.value,
    Role.ADMIN.value,
}

PHARMACY_STAFF = {
    Role.PHARMACIST.value,
    Role.ADMIN.value,
}

LABORATORY_STAFF_MEMBERS = {
    Role.LABORATORY_STAFF.value,
    Role.LAB_TECH.value,
    Role.DOCTOR.value,
    Role.ADMIN.value,
}


def normalize_role(role_str: str) -> str:
    """
    Normalizes role input by stripping whitespace and converting to uppercase.
    Maps common role aliases (e.g. 'lab' -> 'LABORATORY_STAFF').
    """
    if not role_str:
        raise ValueError("Role cannot be empty")
    cleaned = role_str.strip().upper()
    if cleaned in ("LAB", "LAB_STAFF", "LABORATORY"):
        return Role.LABORATORY_STAFF.value
    return cleaned


def validate_role(role_str: str) -> str:
    """
    Validates that a role is one of the supported hospital roles.
    Raises ValueError if unsupported.
    """
    normalized = normalize_role(role_str)
    if normalized not in SUPPORTED_ROLES:
        allowed = ", ".join(sorted(SUPPORTED_ROLES))
        raise ValueError(
            f"Invalid role '{role_str}'. Supported roles are: {allowed}"
        )
    return normalized


# Clinical Permissions Matrix
# Defines which roles can read, create, update, or administer each kind of clinical record.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        # User & Facility administration
        "users:read", "users:create", "users:update", "users:delete",
        "facilities:read", "facilities:create", "facilities:update",
        "wards:read", "wards:create", "wards:update",
        # Clinical records (Admin oversight)
        "patients:read", "patients:create", "patients:update",
        "admissions:read", "admissions:create", "admissions:update",
        "vitals:read", "vitals:create",
        "medications:read", "medications:prescribe", "medications:administer",
        "investigations:read", "investigations:order", "investigations:record",
        "clinical_notes:read", "clinical_notes:create",
        "discharge:read", "discharge:authorize",
        "audit:read",
    },
    Role.DOCTOR.value: {
        # Patient care & admissions
        "patients:read", "patients:create", "patients:update",
        "admissions:read", "admissions:create", "admissions:update",
        # Clinical assessments, prescriptions & reviews
        "vitals:read", "vitals:create",
        "medications:read", "medications:prescribe", "medications:administer",
        "clinical_notes:read", "clinical_notes:create",
        # Diagnostics
        "investigations:read", "investigations:order", "investigations:record",
        # Discharge
        "discharge:read", "discharge:authorize",
        "facilities:read", "wards:read",
    },
    Role.NURSE.value: {
        # Bedside care, monitoring & administration
        "patients:read", "patients:create",
        "admissions:read", "admissions:create",
        "vitals:read", "vitals:create",
        "medications:read", "medications:administer",
        "clinical_notes:read", "clinical_notes:create",
        "investigations:read",
        "discharge:read",
        "facilities:read", "wards:read",
    },
    Role.PHARMACIST.value: {
        # Medication reconciliation, clinical evaluation & dispensing
        "patients:read",
        "admissions:read",
        "medications:read", "medications:dispense",
        "vitals:read",
        "clinical_notes:read",
        "investigations:read",
        "discharge:read",
        "facilities:read", "wards:read",
    },
    Role.LABORATORY_STAFF.value: {
        # Diagnostic sample processing, clinical review correlation & results recording
        "patients:read",
        "admissions:read",
        "investigations:read", "investigations:record",
        "vitals:read",
        "clinical_notes:read",
        "facilities:read", "wards:read",
    },
    Role.LAB_TECH.value: {
        # Laboratory technician alias
        "patients:read",
        "admissions:read",
        "investigations:read", "investigations:record",
        "vitals:read",
        "clinical_notes:read",
        "facilities:read", "wards:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """
    Checks if a role has the specified permission.
    """
    try:
        norm_role = normalize_role(role)
    except ValueError:
        return False
    role_perms = ROLE_PERMISSIONS.get(norm_role, set())
    return permission in role_perms
