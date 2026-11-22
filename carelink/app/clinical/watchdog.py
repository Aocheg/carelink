"""
Clinical Safety Watchdog & In-Process Notification Engine.

Executes proactive patient safety monitoring:
1. Critical NEWS2 physiological deterioration (score >= 5 or critical physiological red flags).
2. Diagnostic turnaround SLA breaches (overdue STAT > 60m and URGENT > 240m lab investigations).
3. Shift handover coverage gaps (> 12 hours without recorded clinical observations or notes).

Engineered with thread-safe anti-fatigue debounce caching and immutable
SHA-256 chained audit trail generation for NDPA 2023 & clinical governance compliance.
"""

from datetime import datetime, timedelta, timezone
import threading
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.clinical.alerts import calculate_news2_score, evaluate_clinical_alerts
from app.clinical.models import ClinicalNote
from app.investigations.models import InvestigationOrder
from app.vitals.models import VitalSign


def _ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ClinicalSafetyWatchdog:
    """
    In-process clinical safety monitor executing automated patient safety sweeps:
    - Critical NEWS2 deterioration (score >= 5 or vital signs red flags)
    - Diagnostic turnaround breaches (overdue STAT & URGENT orders)
    - Shift handover coverage gaps (> 12h without doctor/nursing assessment)
    
    Includes an anti-fatigue debounce cooldown cache (default 30 min) to prevent
    clinical alert desensitization, coupled with SHA-256 chained audit ledgering.
    """

    def __init__(self, cooldown_minutes: int = 30):
        self.cooldown_window = timedelta(minutes=cooldown_minutes)
        self._debounce_cache: dict[str, datetime] = {}
        self._active_alerts: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self.last_scan_at: datetime | None = None
        self.total_scans_run: int = 0

    def clear_cooldown_cache(self) -> None:
        """Flushes the debounce cache and active alerts list (used for testing and shifts)."""
        with self._lock:
            self._debounce_cache.clear()
            self._active_alerts.clear()

    def get_status(self) -> dict[str, Any]:
        """Returns the operational telemetry of the watchdog service."""
        with self._lock:
            return {
                "service": "ClinicalSafetyWatchdog",
                "status": "RUNNING",
                "cooldown_minutes": int(self.cooldown_window.total_seconds() / 60),
                "cached_debounce_keys": len(self._debounce_cache),
                "active_alerts_count": len(self._active_alerts),
                "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
                "total_scans_run": self.total_scans_run,
            }

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Returns a snapshot of current active clinical alerts."""
        with self._lock:
            return list(self._active_alerts)

    def scan_facility_safety(
        self,
        db: Session,
        actor_id: int | None = None,
        force_ignore_cooldown: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Executes a comprehensive safety scan across all currently active inpatient admissions.
        Writes immutable SHA-256 chained audit logs for every newly triggered clinical alert.
        """
        now = datetime.now(timezone.utc)
        generated_alerts: list[dict[str, Any]] = []

        stmt = select(Admission).where(Admission.status == "ACTIVE")
        active_admissions = db.execute(stmt).scalars().all()

        for admission in active_admissions:
            # -------------------------------------------------------------
            # 1. Evaluate vital signs & NEWS2 deterioration
            # -------------------------------------------------------------
            vital_stmt = (
                select(VitalSign)
                .where(VitalSign.admission_id == admission.id)
                .order_by(VitalSign.recorded_at.desc())
            )
            latest_vital = db.execute(vital_stmt).scalars().first()

            if latest_vital:
                news2_score = calculate_news2_score(latest_vital)
                red_flags = evaluate_clinical_alerts(latest_vital)

                if news2_score >= 5 or len(red_flags) > 0:
                    alert_key = f"NEWS2_ALERT:{admission.id}:{news2_score}"
                    with self._lock:
                        last_triggered = self._debounce_cache.get(alert_key)
                        should_alert = (
                            force_ignore_cooldown
                            or last_triggered is None
                            or (now - last_triggered) >= self.cooldown_window
                        )
                        if should_alert:
                            self._debounce_cache[alert_key] = now

                    if should_alert:
                        severity = "CRITICAL" if news2_score >= 7 else "HIGH"
                        alert_data = {
                            "alert_type": "CRITICAL_PHYSIOLOGICAL_DETERIORATION",
                            "severity": severity,
                            "admission_id": admission.id,
                            "patient_id": admission.patient_id,
                            "ward_id": admission.ward_id,
                            "bed_id": admission.bed_id,
                            "news2_score": news2_score,
                            "vital_id": latest_vital.id,
                            "red_flags": red_flags,
                            "message": (
                                f"Urgent clinical review required: Admission {admission.admission_number} "
                                f"exhibits elevated NEWS2 score ({news2_score}) with {len(red_flags)} physiological red flag(s)."
                            ),
                            "triggered_at": now.isoformat(),
                        }
                        generated_alerts.append(alert_data)
                        create_audit_log(
                            db,
                            user_id=actor_id,
                            action="CLINICAL_SAFETY_ALERT",
                            entity_type="admission",
                            entity_id=admission.id,
                            details=f"Watchdog triggered {severity} NEWS2 deterioration alert (Score: {news2_score})",
                        )

            # -------------------------------------------------------------
            # 2. Evaluate Overdue STAT & URGENT Diagnostic Investigations
            # -------------------------------------------------------------
            investigation_stmt = select(InvestigationOrder).where(
                InvestigationOrder.admission_id == admission.id,
                InvestigationOrder.status.in_(["ORDERED", "SAMPLE_COLLECTED"]),
            )
            pending_orders = db.execute(investigation_stmt).scalars().all()

            for order in pending_orders:
                order_time = _ensure_utc(order.ordered_at)
                elapsed_minutes = int((now - order_time).total_seconds() / 60)

                is_overdue = False
                threshold_minutes = 60
                severity = "URGENT"

                if order.urgency == "STAT" and elapsed_minutes >= 60:
                    is_overdue = True
                    threshold_minutes = 60
                    severity = "CRITICAL"
                elif order.urgency == "URGENT" and elapsed_minutes >= 240:
                    is_overdue = True
                    threshold_minutes = 240
                    severity = "HIGH"

                if is_overdue:
                    alert_key = f"OVERDUE_LAB:{order.id}:{order.urgency}"
                    with self._lock:
                        last_triggered = self._debounce_cache.get(alert_key)
                        should_alert = (
                            force_ignore_cooldown
                            or last_triggered is None
                            or (now - last_triggered) >= self.cooldown_window
                        )
                        if should_alert:
                            self._debounce_cache[alert_key] = now

                    if should_alert:
                        alert_data = {
                            "alert_type": "OVERDUE_DIAGNOSTIC_INVESTIGATION",
                            "severity": severity,
                            "admission_id": admission.id,
                            "patient_id": admission.patient_id,
                            "investigation_order_id": order.id,
                            "test_name": order.test_name,
                            "urgency": order.urgency,
                            "elapsed_minutes": elapsed_minutes,
                            "threshold_minutes": threshold_minutes,
                            "message": (
                                f"Diagnostic turnaround breach: {order.urgency} test '{order.test_name}' "
                                f"for Admission {admission.admission_number} is pending ({elapsed_minutes}m elapsed; SLA {threshold_minutes}m)."
                            ),
                            "triggered_at": now.isoformat(),
                        }
                        generated_alerts.append(alert_data)
                        create_audit_log(
                            db,
                            user_id=actor_id,
                            action="CLINICAL_SAFETY_ALERT",
                            entity_type="investigation_order",
                            entity_id=order.id,
                            details=f"Watchdog triggered overdue {order.urgency} investigation alert: {order.test_name}",
                        )

            # -------------------------------------------------------------
            # 3. Evaluate Overdue Shift Handover Review (> 12 hours)
            # -------------------------------------------------------------
            admitted_time = _ensure_utc(admission.admitted_at)
            stay_duration_hours = (now - admitted_time).total_seconds() / 3600

            if stay_duration_hours >= 12:
                cutoff_time = now - timedelta(hours=12)
                recent_note_stmt = select(ClinicalNote).where(
                    ClinicalNote.admission_id == admission.id,
                    ClinicalNote.created_at >= cutoff_time,
                )
                recent_note = db.execute(recent_note_stmt).scalars().first()

                recent_vital_stmt = select(VitalSign).where(
                    VitalSign.admission_id == admission.id,
                    VitalSign.recorded_at >= cutoff_time,
                )
                recent_vital = db.execute(recent_vital_stmt).scalars().first()

                if not recent_note and not recent_vital:
                    alert_key = f"OVERDUE_HANDOVER_REVIEW:{admission.id}"
                    with self._lock:
                        last_triggered = self._debounce_cache.get(alert_key)
                        should_alert = (
                            force_ignore_cooldown
                            or last_triggered is None
                            or (now - last_triggered) >= self.cooldown_window
                        )
                        if should_alert:
                            self._debounce_cache[alert_key] = now

                    if should_alert:
                        alert_data = {
                            "alert_type": "OVERDUE_SHIFT_HANDOVER_REVIEW",
                            "severity": "WARNING",
                            "admission_id": admission.id,
                            "patient_id": admission.patient_id,
                            "ward_id": admission.ward_id,
                            "bed_id": admission.bed_id,
                            "message": (
                                f"Shift handover safety check: Admission {admission.admission_number} "
                                f"has no clinical notes or observations recorded in the past 12 hours."
                            ),
                            "triggered_at": now.isoformat(),
                        }
                        generated_alerts.append(alert_data)
                        create_audit_log(
                            db,
                            user_id=actor_id,
                            action="CLINICAL_SAFETY_ALERT",
                            entity_type="admission",
                            entity_id=admission.id,
                            details=f"Watchdog triggered overdue shift review alert for admission {admission.admission_number}",
                        )

        # Update service telemetry
        with self._lock:
            self._active_alerts = generated_alerts
            self.last_scan_at = now
            self.total_scans_run += 1

        return generated_alerts


# Global singleton instance for in-process application lifecycle
watchdog = ClinicalSafetyWatchdog(cooldown_minutes=30)
