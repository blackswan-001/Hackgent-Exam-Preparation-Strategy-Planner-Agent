"""
agent.py — LLM reasoning layer using Groq.
Handles all generative tasks: strategy explanation, timetable, mini goals.
No arithmetic here — trust the pre-computed state from tools.py.
"""

import os
import time
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState, SYSTEM_PROMPT, StrategyMode


# ─────────────────────────────────────────────
# Model Fallback Chain (Groq free tier)
# ─────────────────────────────────────────────

# Groq free tier is generous: ~30 RPM, 6000 RPD per model
# Models tried in order on rate limit
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",   # Primary — best quality, fast
    "llama-3.1-8b-instant",      # Fallback — ultra-fast, lighter
]

RATE_LIMIT_WAIT = 20  # seconds to wait on per-minute 429


def get_llm(model: str) -> ChatGroq:
    """Initialize and return a Groq LLM for a specific model."""
    api_key = os.environ.get("GROQ_API_KEY", "API_KEY_GOES_HERE")
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=0.7,
    )


def invoke_with_fallback(messages: list) -> str:
    """
    Try each model in FALLBACK_MODELS in order.

    429 behaviour:
      - Parse retry delay from error if present, else wait RATE_LIMIT_WAIT seconds.
      - Retry the same model up to 3 times before switching.

    Other errors:
      - Raise immediately.
    """
    last_error = None

    for model_name in FALLBACK_MODELS:
        print(f"[agent] Trying model: {model_name}")
        llm = get_llm(model_name)
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                response = llm.invoke(messages)
                content = response.content if response.content is not None else ""
                print(f"[agent] Success with model: {model_name}")
                return content

            except Exception as e:
                err_str = str(e)
                last_error = e

                if "429" in err_str or "rate_limit" in err_str.lower() or "rate limit" in err_str.lower():
                    wait = _extract_retry_delay(err_str) or RATE_LIMIT_WAIT
                    print(f"[agent] Rate limit on {model_name}. "
                          f"Waiting {wait}s (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(wait)
                    continue  # retry same model

                else:
                    # Non-retriable error — skip to next model
                    print(f"[agent] Error on {model_name}: {err_str[:120]}")
                    break

        print(f"[agent] Switching from {model_name} to next model...")

    raise RuntimeError(
        "All Groq models failed.\n\n"
        f"Last error: {last_error}\n\n"
        "Check your API key or wait a minute and retry."
    )


def _extract_retry_delay(err_str: str) -> int:
    """
    Try to parse a retry delay in seconds from the error string.
    Returns int seconds or None if not found.
    """
    import re
    # Groq errors often say "Please try again in 20.5s"
    match = re.search(r"try again in\s+([\d.]+)s", err_str, re.IGNORECASE)
    if match:
        return int(float(match.group(1))) + 2
    match = re.search(r"retry.{0,20}?(\d+)\s*s", err_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) + 2
    return None


# ─────────────────────────────────────────────
# Prompt Builder
# ─────────────────────────────────────────────

def build_planning_prompt(state: AgentState) -> str:
    """
    Construct the human-turn prompt from agent state.
    All computations are already done — we just format them for the LLM.
    """
    subjects    = state["subjects"]
    mode        = state["strategy_mode"]
    days        = state["days_remaining"]
    total_hours = state["total_study_hours"]
    time_blocks = state["available_time_blocks"]
    syllabus    = state.get("syllabus_context") or ""
    syllabus    = syllabus if syllabus is not None else ""
    daily_hours = state["daily_study_hours"]

    # Format subject list
    subject_lines = []
    for s in subjects:
        subject_lines.append(
            f"  - {s['name']} | Confidence: {s['confidence']}/10 | "
            f"{s['priority_label']} | Allocated: {s['allocated_hours']}h"
        )
    subject_block = "\n".join(subject_lines)

    # Format time blocks
    block_str = ", ".join(time_blocks) if time_blocks else "09:00-11:00, 14:00-16:00"

    # Optional syllabus
    syllabus_section = ""
    if syllabus and syllabus.strip():
        syllabus_section = f"""
SYLLABUS CONTEXT (use to enrich mini goals with specific topics):
{syllabus[:1500]}
"""

    # Mode-specific instructions
    if mode == StrategyMode.INTENSIVE:
        mode_instructions = """
INTENSIVE REVISION MODE ACTIVE:
- Focus heavily on High Priority subjects first.
- Include past-paper practice blocks every day.
- Revision cycles: morning theory review, evening practice problems.
- Minimize subject switching — depth over breadth.
"""
    else:
        mode_instructions = """
PROGRESSIVE MASTERY MODE ACTIVE:
- Rotate subjects daily for balanced coverage.
- Include a weekly revision checkpoint (if 7+ days remain).
- Build foundational understanding before going deep.
- Use spaced repetition — revisit earlier topics after 3 days.
"""

    prompt = f"""
You are the Exam Preparation Strategy Agent.

STUDENT PROFILE:
- Days until exam: {days}
- Strategy Mode: {mode.value}
- Daily study hours: {daily_hours}h
- Total available study hours: {total_hours}h

SUBJECTS (hours already computed — do NOT change them):
{subject_block}

DAILY STUDY TIME BLOCKS:
{block_str}

{mode_instructions}
{syllabus_section}

Generate the full exam preparation strategy using this exact structure:

## Strategy Overview
Write 2-3 sentences explaining the approach given the student's constraints and mode.

## Day-by-Day Timetable
For every single day from Day 1 to Day {days}, write:

### Day [N] - [Day of week]
| Time Block | Subject | Focus Area | Duration |
|------------|---------|------------|----------|
| [time]     | [name]  | [activity] | [X]h     |

Mini Goals:
- Educational: [specific, actionable study task]
- Fun: [creative, playful but relevant task]

## Revision Strategy
2-3 sentences on the overall revision approach across all days.

## Final Motivation
One warm, energizing sentence to close.

RULES:
- Use the EXACT allocated hours given. Do not recalculate.
- Alternate mini goals: educational then fun, every day.
- Output clean markdown only.
"""
    return prompt.strip()


# ─────────────────────────────────────────────
# Main Agent Call
# ─────────────────────────────────────────────

def run_planning_agent(state: AgentState) -> str:
    """
    Run the planning agent with the current state.
    Returns the full formatted markdown output.
    """
    prompt = build_planning_prompt(state)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    print("[agent] Invoking Groq planning agent...")
    return invoke_with_fallback(messages)


# ─────────────────────────────────────────────
# Quick Strategy Preview
# ─────────────────────────────────────────────

def run_quick_strategy_preview(state: AgentState) -> str:
    """
    Generate a quick 2-sentence strategy preview.
    Used for Gradio streaming feel before full plan loads.
    """
    mode = state["strategy_mode"]
    days = state["days_remaining"]
    subjects = state["subjects"]
    top_subject = max(subjects, key=lambda s: s["weight"])

    quick_prompt = f"""
In exactly 2 sentences, describe the exam preparation strategy for a student with:
- {days} days remaining
- Mode: {mode.value}
- Most critical subject: {top_subject['name']} (confidence {top_subject['confidence']}/10)

Be warm, precise, and motivating.
"""
    messages = [
        SystemMessage(content="You are a concise academic planning assistant."),
        HumanMessage(content=quick_prompt),
    ]
    return invoke_with_fallback(messages)
