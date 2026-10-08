"""
Deterministic clinical alert rules and Early Warning Score (NEWS2) calculation.
Provides deterministic, testable clinical safety algorithms.
"""

from typing import Any


def calculate_news2_score(vitals: Any) -> int:
    """
    Computes deterministic NEWS2 score (National Early Warning Score)
    based on physiological parameters.
    """
    score = 0

    # 1. Respiration Rate (/min)
    rr = getattr(vitals, "respiratory_rate", None)
    if rr is not None:
        if rr <= 8 or rr >= 25:
            score += 3
        elif 21 <= rr <= 24:
            score += 2
        elif 9 <= rr <= 11:
            score += 1

    # 2. Oxygen Saturation SpO2 (%)
    spo2 = getattr(vitals, "spo2", None)
    if spo2 is not None:
        if spo2 <= 91:
            score += 3
        elif 92 <= spo2 <= 93:
            score += 2
        elif 94 <= spo2 <= 95:
            score += 1

    # 3. Systolic Blood Pressure (mmHg)
    sbp = getattr(vitals, "systolic_bp", None)
    if sbp is not None:
        if sbp <= 90 or sbp >= 220:
            score += 3
        elif 91 <= sbp <= 100:
            score += 2
        elif 101 <= sbp <= 110:
            score += 1

    # 4. Pulse / Heart Rate (bpm)
    pulse = getattr(vitals, "pulse", None)
    if pulse is not None:
        if pulse <= 40 or pulse >= 131:
            score += 3
        elif 111 <= pulse <= 130:
            score += 2
        elif (41 <= pulse <= 50) or (91 <= pulse <= 110):
            score += 1

    # 5. Temperature (°C)
    temp = getattr(vitals, "temperature", None)
    if temp is not None:
        if temp <= 35.0:
            score += 3
        elif temp >= 39.1:
            score += 2
        elif (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
            score += 1

    return score


def evaluate_clinical_alerts(vitals: Any) -> list[dict]:
    """
    Evaluates individual vital sign parameters against clinical red-flag thresholds.
    Returns a list of structured alert objects.
    """
    alerts = []

    # Blood Pressure
    sbp = getattr(vitals, "systolic_bp", None)
    dbp = getattr(vitals, "diastolic_bp", None)
    if sbp is not None:
        if sbp < 90:
            alerts.append({
                "parameter": "BLOOD_PRESSURE",
                "severity": "CRITICAL",
                "message": f"Severe hypotension (Systolic BP {sbp} mmHg < 90 mmHg). Risk of circulatory shock.",
                "action": "Immediate medical review and IV fluid assessment.",
            })
        elif sbp >= 180 or (dbp is not None and dbp >= 120):
            alerts.append({
                "parameter": "BLOOD_PRESSURE",
                "severity": "CRITICAL",
                "message": f"Hypertensive emergency (BP {sbp}/{dbp or '-'} mmHg). Risk of acute end-organ damage.",
                "action": "Urgent medical review for controlled antihypertensive therapy.",
            })

    # Oxygen Saturation (SpO2)
    spo2 = getattr(vitals, "spo2", None)
    if spo2 is not None:
        if spo2 < 88.0:
            alerts.append({
                "parameter": "SPO2",
                "severity": "CRITICAL",
                "message": f"Critical hypoxia (SpO2 {spo2}% < 88%).",
                "action": "Immediate high-flow oxygen and airway evaluation.",
            })
        elif spo2 < 92.0:
            alerts.append({
                "parameter": "SPO2",
                "severity": "WARNING",
                "message": f"Hypoxia (SpO2 {spo2}% < 92%).",
                "action": "Supplemental oxygen and respiratory assessment.",
            })

    # Heart Rate / Pulse
    pulse = getattr(vitals, "pulse", None)
    if pulse is not None:
        if pulse > 130:
            alerts.append({
                "parameter": "PULSE",
                "severity": "CRITICAL",
                "message": f"Severe tachycardia (Pulse {pulse} bpm > 130 bpm).",
                "action": "12-lead ECG, hemodynamic check, and urgent review.",
            })
        elif pulse < 45:
            alerts.append({
                "parameter": "PULSE",
                "severity": "CRITICAL",
                "message": f"Severe bradycardia (Pulse {pulse} bpm < 45 bpm).",
                "action": "Atropine availability check and urgent medical review.",
            })

    # Temperature
    temp = getattr(vitals, "temperature", None)
    if temp is not None:
        if temp >= 38.5:
            alerts.append({
                "parameter": "TEMPERATURE",
                "severity": "WARNING",
                "message": f"High fever (Temperature {temp}°C >= 38.5°C). Sepsis screening recommended.",
                "action": "Blood cultures, antipyretics, and infection source identification.",
            })
        elif temp < 35.0:
            alerts.append({
                "parameter": "TEMPERATURE",
                "severity": "CRITICAL",
                "message": f"Hypothermia (Temperature {temp}°C < 35.0°C).",
                "action": "Active warming and hemodynamic monitoring.",
            })

    # Respiratory Rate
    rr = getattr(vitals, "respiratory_rate", None)
    if rr is not None:
        if rr > 24:
            alerts.append({
                "parameter": "RESPIRATORY_RATE",
                "severity": "WARNING",
                "message": f"Tachypnea (Respiratory Rate {rr}/min > 24/min).",
                "action": "Assess work of breathing and arterial blood gases.",
            })
        elif rr < 8:
            alerts.append({
                "parameter": "RESPIRATORY_RATE",
                "severity": "CRITICAL",
                "message": f"Severe bradypnea (Respiratory Rate {rr}/min < 8/min). Respiratory arrest risk.",
                "action": "Bag-valve-mask readiness and immediate medical intervention.",
            })

    return alerts
