from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clinical.schemas import (
    ClinicalNoteCreate,
    ClinicalNoteResponse,
    HandoverSummary,
    TimelineEvent,
)
from app.clinical.service import (
    create_clinical_note,
    generate_handover_summary,
    get_admission_alerts,
    get_clinical_notes_by_admission,
    get_unified_clinical_timeline,
)
from app.database.connection import SessionLocal

router = APIRouter(
    prefix="/clinical",
    tags=["Clinical"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/notes",
    response_model=ClinicalNoteResponse,
    status_code=201,
)
def create_clinical_note_endpoint(
    note: ClinicalNoteCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_clinical_note(db, note)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get(
    "/notes/admission/{admission_id}",
    response_model=list[ClinicalNoteResponse],
)
def get_clinical_notes_endpoint(
    admission_id: int,
    note_type: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        return get_clinical_notes_by_admission(db, admission_id, note_type=note_type)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get(
    "/handover/{admission_id}",
    response_model=HandoverSummary,
)
def get_handover_summary_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return generate_handover_summary(db, admission_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get(
    "/timeline/{admission_id}",
    response_model=list[TimelineEvent],
)
def get_unified_clinical_timeline_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_unified_clinical_timeline(db, admission_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get(
    "/alerts/{admission_id}",
)
def get_admission_alerts_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_admission_alerts(db, admission_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
