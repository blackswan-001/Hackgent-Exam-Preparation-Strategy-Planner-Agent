"""
workflow.py — LangGraph workflow for the Exam Preparation Strategy Agent.
Clean, shallow graph: Preprocess → Plan → END
No recursive loops. Intentionally simple. Hackathon-grade stable.
"""

from langgraph.graph import StateGraph, END

from state import AgentState
from tools import build_initial_state
from agent import run_planning_agent, run_quick_strategy_preview


# ─────────────────────────────────────────────
# Node: Preprocess (Tools Execution)
# ─────────────────────────────────────────────

def preprocess_node(state: AgentState) -> AgentState:
    """
    Node 1: Run all deterministic computations.
    Validates inputs and enriches state before LLM reasoning.
    """
    print("[workflow] Node: preprocess_node")

    # Validate days remaining
    days = state.get("days_remaining", 0)
    if days <= 0:
        raise ValueError("Exam date must be in the future.")

    # Validate subjects
    if not state.get("subjects"):
        raise ValueError("No subjects found. Please enter at least one subject.")

    # Log strategy mode selection
    mode = state["strategy_mode"]
    print(f"[workflow] Strategy Mode Selected: {mode.value}")
    print(f"[workflow] Days Remaining: {days}")
    print(f"[workflow] Subjects: {[s['name'] for s in state['subjects']]}")

    return state


# ─────────────────────────────────────────────
# Node: LLM Planning
# ─────────────────────────────────────────────

def planning_node(state: AgentState) -> AgentState:
    """
    Node 2: Call Gemini to generate the full strategy + timetable.
    Injects result into state["final_output"].
    """
    print("[workflow] Node: planning_node — invoking Gemini...")
    final_output = run_planning_agent(state)
    state["final_output"] = final_output
    print("[workflow] Planning complete.")
    return state


# ─────────────────────────────────────────────
# Graph Definition
# ─────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Construct and compile the LangGraph workflow.
    Flow: START → preprocess → planning → END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("planning", planning_node)

    # Define edges
    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "planning")
    graph.add_edge("planning", END)

    return graph.compile()


# ─────────────────────────────────────────────
# Runner — Main Entry for main.py
# ─────────────────────────────────────────────

def run_agent(
    subjects_raw: str,
    confidence_scores: dict,
    exam_date: str,
    daily_study_hours: float,
    lifestyle: dict = None,
    syllabus_context: str = None,
) -> str:
    """
    Full agent runner. Builds initial state, runs LangGraph, returns output.

    Args:
        subjects_raw: Comma-separated subject names
        confidence_scores: Dict of {subject_name: confidence_int}
        exam_date: "YYYY-MM-DD"
        daily_study_hours: float
        lifestyle: Optional LifestyleBlock dict
        syllabus_context: Optional extracted text from .docx

    Returns:
        Formatted markdown string of the complete exam strategy.
    """
    # Step 1: Build initial state from deterministic tools
    print("[workflow] Building initial state...")
    initial_state = build_initial_state(
        subjects_raw=subjects_raw,
        confidence_scores=confidence_scores,
        exam_date=exam_date,
        daily_study_hours=daily_study_hours,
        lifestyle=lifestyle,
        syllabus_context=syllabus_context,
    )

    # Step 2: Compile and run LangGraph workflow
    print("[workflow] Compiling workflow graph...")
    app = build_workflow()

    print("[workflow] Running graph...")
    final_state = app.invoke(initial_state)

    return final_state.get("final_output", "⚠️ Agent returned no output. Please try again.")


# ─────────────────────────────────────────────
# Quick Preview Runner (for Gradio progress feel)
# ─────────────────────────────────────────────

def run_preview(
    subjects_raw: str,
    confidence_scores: dict,
    exam_date: str,
    daily_study_hours: float,
) -> str:
    """
    Generate a quick 2-sentence strategy preview before full run.
    Used to give Gradio a "fast response" feel.
    """
    from tools import (
        calculate_days_remaining,
        determine_strategy_mode,
        compute_subject_allocations,
        calculate_total_study_hours,
    )

    days = calculate_days_remaining(exam_date)
    total_hours = calculate_total_study_hours(days, daily_study_hours)
    mode = determine_strategy_mode(days)
    subjects = compute_subject_allocations(subjects_raw, confidence_scores, total_hours)

    preview_state: AgentState = {
        "subjects_raw": subjects_raw,
        "exam_date": exam_date,
        "daily_study_hours": daily_study_hours,
        "lifestyle": None,
        "syllabus_context": None,
        "days_remaining": days,
        "total_study_hours": total_hours,
        "available_time_blocks": [],
        "subjects": subjects,
        "strategy_mode": mode,
        "strategy_explanation": "",
        "timetable": [],
        "mini_goals": [],
        "motivation_line": "",
        "final_output": "",
    }

    return run_quick_strategy_preview(preview_state)
