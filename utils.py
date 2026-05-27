"""
utils.py — Utility helpers for the Exam Preparation Strategy Agent.
Keeps main.py and tools.py clean from one-off helpers.
All functions guard against None inputs from Gradio.
"""

import re
import os
from typing import Dict, Tuple, List, Optional


# ─────────────────────────────────────────────
# Subject + Confidence Parser
# ─────────────────────────────────────────────

def parse_subjects_and_confidence(
    subjects_input: str,
    confidence_input: str
) -> Tuple[str, Dict[str, int]]:
    """
    Parse raw subject and confidence inputs from Gradio UI.

    subjects_input:   "Math, Physics, Chemistry"
    confidence_input: "Math:4, Physics:7, Chemistry:9"
                   OR "4, 7, 9" (positional)

    Returns:
        subjects_raw: cleaned comma-separated string
        confidence_scores: {"Math": 4, "Physics": 7, ...}
    """
    # Guard None — Gradio can pass None for empty fields
    subjects_input   = subjects_input   or ""
    confidence_input = confidence_input or ""

    subject_names = [s.strip() for s in subjects_input.split(",") if s.strip()]
    subjects_raw = ", ".join(subject_names)
    confidence_scores: Dict[str, int] = {}

    if not confidence_input.strip():
        # Default: mid-confidence for all
        for name in subject_names:
            confidence_scores[name] = 5
        return subjects_raw, confidence_scores

    # Try "Subject:score" format
    if ":" in confidence_input:
        for entry in confidence_input.split(","):
            entry = entry.strip()
            if ":" in entry:
                parts = entry.split(":", 1)
                name = parts[0].strip()
                try:
                    score = int(parts[1].strip())
                    score = max(1, min(10, score))
                    confidence_scores[name] = score
                except ValueError:
                    pass
    else:
        # Positional: scores match subject order
        scores = [s.strip() for s in confidence_input.split(",")]
        for i, name in enumerate(subject_names):
            if i < len(scores):
                try:
                    score = int(scores[i])
                    score = max(1, min(10, score))
                    confidence_scores[name] = score
                except ValueError:
                    confidence_scores[name] = 5
            else:
                confidence_scores[name] = 5

    # Fill any missing subjects with default
    for name in subject_names:
        if name not in confidence_scores:
            confidence_scores[name] = 5

    return subjects_raw, confidence_scores


# ─────────────────────────────────────────────
# Lifestyle Block Builder
# ─────────────────────────────────────────────

def build_lifestyle_block(
    wake_time: str,
    sleep_time: str,
    meal_slots_raw: str,
    routine_slots_raw: str,
    intensive_mode: bool = False
) -> Optional[dict]:
    """
    Build a LifestyleBlock dict from Gradio form inputs.
    Returns None if all inputs are default, so tools.py uses its own defaults.
    """
    # Coerce None to safe defaults before any .strip() calls
    wake_time         = wake_time         or "07:00"
    sleep_time        = sleep_time        or "22:00"
    meal_slots_raw    = meal_slots_raw    or ""
    routine_slots_raw = routine_slots_raw or ""

    is_default = (
        wake_time in ("", "07:00") and
        sleep_time in ("", "22:00") and
        not meal_slots_raw.strip() and
        not routine_slots_raw.strip()
    )

    if is_default and not intensive_mode:
        return None

    meal_slots = _parse_slot_list(meal_slots_raw) or ["08:00-08:30", "13:00-13:30", "19:00-19:30"]
    routine_slots = _parse_slot_list(routine_slots_raw)

    return {
        "wake_time": wake_time,
        "sleep_time": sleep_time,
        "meal_slots": meal_slots,
        "routine_slots": routine_slots,
    }


def _parse_slot_list(raw: str) -> List[str]:
    """Parse newline or comma-separated time slots. Safe against None."""
    if not raw:
        return []
    if not raw.strip():
        return []
    slots = re.split(r"[,\n]", raw)
    return [s.strip() for s in slots if s.strip()]


# ─────────────────────────────────────────────
# File Handler for .docx Upload
# ─────────────────────────────────────────────

def handle_file_upload(file_obj) -> str:
    """
    Handle Gradio file upload object.
    Extracts text from .docx safely.
    Returns empty string on any failure.
    """
    if file_obj is None:
        return ""

    try:
        from tools import extract_docx_text
        file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)

        if not file_path.endswith(".docx"):
            return ""

        extracted = extract_docx_text(file_path)
        if extracted:
            print(f"[utils] Extracted {len(extracted)} chars from docx")
        return extracted or ""
    except Exception as e:
        print(f"[utils] File handling error: {e}")
        return ""


# ─────────────────────────────────────────────
# Output Formatter
# ─────────────────────────────────────────────

def format_agent_output(raw_output: str, strategy_mode: str, days_remaining: int) -> str:
    """Prepend a clean header to the agent's markdown output."""
    raw_output = raw_output or ""
    mode_emoji = "🚨" if "Intensive" in strategy_mode else "📘"
    header = (
        f"# 🎓 Exam Preparation Strategy Agent\n"
        f"**Mode:** {mode_emoji} {strategy_mode} | "
        f"**Days Remaining:** {days_remaining}\n\n---\n\n"
    )
    return header + raw_output


# ─────────────────────────────────────────────
# Input Validation
# ─────────────────────────────────────────────

def validate_inputs(
    subjects_input: str,
    exam_date: str,
    daily_hours: float,
) -> Tuple[bool, str]:
    """
    Validate core inputs before running the agent.
    Returns (is_valid, error_message).
    """
    subjects_input = subjects_input or ""
    exam_date      = exam_date      or ""

    if not subjects_input.strip():
        return False, "⚠️ Please enter at least one subject."

    if not exam_date:
        return False, "⚠️ Please select an exam date."

    from datetime import date, datetime
    try:
        parsed = datetime.strptime(exam_date, "%Y-%m-%d").date()
        if parsed <= date.today():
            return False, "⚠️ Exam date must be in the future."
    except ValueError:
        return False, "⚠️ Invalid date format. Use YYYY-MM-DD."

    daily_hours = float(daily_hours or 0)
    if daily_hours < 0.5:
        return False, "⚠️ Daily study hours must be at least 0.5."

    if daily_hours > 18:
        return False, "⚠️ Daily study hours cannot exceed 18. You need sleep. 🛌"

    return True, ""


# ─────────────────────────────────────────────
# Summary Card
# ─────────────────────────────────────────────

def build_summary_card(
    subjects: list,
    days_remaining: int,
    total_hours: float,
    strategy_mode: str,
) -> str:
    """Build a quick summary markdown card shown before full output."""
    lines = [
        f"### 📋 Planning Summary",
        f"- **Days Remaining:** {days_remaining}",
        f"- **Total Study Hours:** {total_hours}h",
        f"- **Strategy Mode:** {strategy_mode}",
        f"",
        f"**Subject Allocations:**",
    ]
    for s in subjects:
        bar_filled = min(int(s['weight'] * 10), 15)
        bar = "█" * bar_filled + "░" * (15 - bar_filled)
        lines.append(
            f"- **{s['name']}** — {s['priority_label']} | "
            f"`{bar}` {s['allocated_hours']}h"
        )
    return "\n".join(lines)
