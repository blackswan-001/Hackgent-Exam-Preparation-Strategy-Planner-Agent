"""
tools.py — Deterministic tools for the Exam Preparation Strategy Agent.
No LLM calls here. Pure Python logic only.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from state import SubjectEntry, LifestyleBlock, StrategyMode


# ─────────────────────────────────────────────
# 1. Days Remaining Calculator
# ─────────────────────────────────────────────

def calculate_days_remaining(exam_date_str: str) -> int:
    """Calculate how many days remain until the exam date."""
    today = date.today()
    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {exam_date_str}. Use YYYY-MM-DD.")
    
    delta = (exam_date - today).days
    return max(delta, 1)  # minimum 1 day to avoid zero-division


# ─────────────────────────────────────────────
# 2. Strategy Mode Selector
# ─────────────────────────────────────────────

INTENSIVE_THRESHOLD = 5  # days

def determine_strategy_mode(days_remaining: int) -> StrategyMode:
    """Determine strategy mode based on days remaining."""
    if days_remaining <= INTENSIVE_THRESHOLD:
        return StrategyMode.INTENSIVE
    return StrategyMode.PROGRESSIVE


# ─────────────────────────────────────────────
# 3. Confidence → Priority Label + Weight
# ─────────────────────────────────────────────

def confidence_to_weight(confidence: int) -> Tuple[str, float]:
    """
    Map confidence score (1–10) to priority label and hour weight multiplier.
    Lower confidence = more study time needed.
    """
    if confidence <= 5:
        return "High Priority", 1.5
    elif confidence <= 8:
        return "Mid Priority", 1.0
    else:
        return "Low Priority", 0.7


# ─────────────────────────────────────────────
# 4. Subject Hour Distributor
# ─────────────────────────────────────────────

def compute_subject_allocations(
    subjects_raw: str,
    confidence_scores: Dict[str, int],
    total_study_hours: float
) -> List[SubjectEntry]:
    """
    Parse subjects and compute weighted hour allocations.
    subjects_raw: comma-separated subject names
    confidence_scores: {"Math": 4, "Physics": 7, ...}
    total_study_hours: total available hours across all days
    """
    subject_names = [s.strip() for s in (subjects_raw or "").split(",") if s.strip()]
    
    entries: List[SubjectEntry] = []
    total_weight = 0.0

    # Compute weights
    for name in subject_names:
        confidence = confidence_scores.get(name, 5)  # default mid-confidence
        confidence = max(1, min(10, int(confidence)))
        priority_label, weight = confidence_to_weight(confidence)
        total_weight += weight
        entries.append({
            "name": name,
            "confidence": confidence,
            "priority_label": priority_label,
            "weight": weight,
            "allocated_hours": 0.0  # computed below
        })

    # Distribute hours proportionally
    for entry in entries:
        proportion = entry["weight"] / total_weight
        entry["allocated_hours"] = round(proportion * total_study_hours, 1)

    return entries


# ─────────────────────────────────────────────
# 5. Lifestyle-Aware Time Block Generator
# ─────────────────────────────────────────────

def compute_available_time_blocks(
    lifestyle: Optional[LifestyleBlock],
    daily_study_hours: float
) -> List[str]:
    """
    Generate daily available study time blocks based on lifestyle inputs.
    Returns a list of time block strings like ["09:00–11:00", "15:00–17:00"].
    Falls back to default if no lifestyle provided.
    """
    if lifestyle is None:
        return _default_time_blocks(daily_study_hours)

    wake = _parse_time(lifestyle.get("wake_time", "07:00"))
    sleep = _parse_time(lifestyle.get("sleep_time", "22:00"))
    
    # Collect all blocked intervals
    blocked: List[Tuple[datetime, datetime]] = []

    # Meal slots
    for slot in lifestyle.get("meal_slots", ["08:00-08:30", "13:00-13:30", "19:00-19:30"]):
        start, end = _parse_slot(slot)
        if start and end:
            blocked.append((start, end))
            # Add 15-min buffer after meals
            blocked.append((end, end + timedelta(minutes=15)))

    # Routine slots
    for slot in lifestyle.get("routine_slots", []):
        start, end = _parse_slot(slot)
        if start and end:
            blocked.append((start, end))

    # Sort blocked intervals
    blocked.sort(key=lambda x: x[0])

    # Generate free windows between wake and sleep
    free_blocks = _find_free_windows(wake, sleep, blocked, daily_study_hours)
    return free_blocks


def _parse_time(time_str: str) -> datetime:
    base = datetime.today().replace(second=0, microsecond=0)
    t = datetime.strptime((time_str or "00:00").strip(), "%H:%M")
    return base.replace(hour=t.hour, minute=t.minute)


def _parse_slot(slot: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    try:
        if not slot:
            return None, None
        parts = slot.replace("–", "-").split("-")
        start = _parse_time(parts[0])
        end = _parse_time(parts[1])
        return start, end
    except Exception:
        return None, None


def _find_free_windows(
    wake: datetime,
    sleep: datetime,
    blocked: List[Tuple[datetime, datetime]],
    target_hours: float
) -> List[str]:
    """Find free windows and split into ~2-hour study blocks."""
    study_block_minutes = 120  # 2-hour blocks
    blocks = []
    cursor = wake + timedelta(minutes=30)  # 30-min morning buffer

    remaining_minutes = target_hours * 60

    for block_start, block_end in blocked:
        if cursor < block_start and remaining_minutes > 0:
            window_minutes = (block_start - cursor).seconds // 60
            if window_minutes >= 60:  # minimum 1-hour window
                usable = min(window_minutes, study_block_minutes, remaining_minutes)
                end_time = cursor + timedelta(minutes=usable)
                blocks.append(f"{cursor.strftime('%H:%M')}–{end_time.strftime('%H:%M')}")
                remaining_minutes -= usable
        cursor = max(cursor, block_end)

    # Check remaining window before sleep
    if cursor < sleep and remaining_minutes > 0:
        window_minutes = (sleep - cursor - timedelta(hours=1)).seconds // 60
        if window_minutes >= 60:
            usable = min(window_minutes, remaining_minutes)
            end_time = cursor + timedelta(minutes=usable)
            blocks.append(f"{cursor.strftime('%H:%M')}–{end_time.strftime('%H:%M')}")

    return blocks if blocks else _default_time_blocks(target_hours)


def _default_time_blocks(daily_study_hours: float) -> List[str]:
    """Fallback time blocks when no lifestyle data provided."""
    blocks = []
    hour_slots = [
        ("09:00", "11:00"),
        ("14:00", "16:00"),
        ("19:00", "21:00"),
        ("21:00", "22:00"),
    ]
    remaining = daily_study_hours
    for start, end in hour_slots:
        if remaining <= 0:
            break
        s = datetime.strptime(start, "%H:%M")
        e = datetime.strptime(end, "%H:%M")
        slot_hours = (e - s).seconds / 3600
        actual = min(slot_hours, remaining)
        actual_end = s + timedelta(hours=actual)
        blocks.append(f"{start}–{actual_end.strftime('%H:%M')}")
        remaining -= actual
    return blocks


# ─────────────────────────────────────────────
# 6. Total Study Hours Calculator
# ─────────────────────────────────────────────

def calculate_total_study_hours(days_remaining: int, daily_study_hours: float) -> float:
    """Compute total available study hours across all remaining days."""
    return round(days_remaining * daily_study_hours, 1)


# ─────────────────────────────────────────────
# 7. Word Document Parser (.docx)
# ─────────────────────────────────────────────

def extract_docx_text(file_path: str, max_chars: int = 2000) -> str:
    """
    Extract plain text from a .docx file.
    Safely truncated to max_chars to avoid LLM overflow.
    Returns empty string if parsing fails.
    """
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
        return full_text[:max_chars]
    except Exception as e:
        print(f"[tools] docx parsing failed: {e}")
        return ""


# ─────────────────────────────────────────────
# 8. State Builder (Convenience)
# ─────────────────────────────────────────────

def build_initial_state(
    subjects_raw: str,
    confidence_scores: Dict[str, int],
    exam_date: str,
    daily_study_hours: float,
    lifestyle: Optional[LifestyleBlock] = None,
    syllabus_context: Optional[str] = None,
) -> dict:
    """
    Run all deterministic computations and return a populated partial state.
    Called before the LangGraph workflow begins.
    """
    days_remaining = calculate_days_remaining(exam_date)
    total_study_hours = calculate_total_study_hours(days_remaining, daily_study_hours)
    strategy_mode = determine_strategy_mode(days_remaining)
    subjects = compute_subject_allocations(subjects_raw, confidence_scores, total_study_hours)
    available_time_blocks = compute_available_time_blocks(lifestyle, daily_study_hours)

    return {
        "subjects_raw": subjects_raw,
        "exam_date": exam_date,
        "daily_study_hours": daily_study_hours,
        "lifestyle": lifestyle,
        "syllabus_context": syllabus_context,
        "days_remaining": days_remaining,
        "total_study_hours": total_study_hours,
        "available_time_blocks": available_time_blocks,
        "subjects": subjects,
        "strategy_mode": strategy_mode,
        "strategy_explanation": "",
        "timetable": [],
        "mini_goals": [],
        "motivation_line": "",
        "final_output": "",
    }
