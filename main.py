"""
main.py — Gradio UI + App orchestration for the Exam Preparation Strategy Agent.
No logic here. Purely UI construction + workflow invocation.
"""

import os
import gradio as gr

from workflow import run_agent
from tools import (
    calculate_days_remaining,
    determine_strategy_mode,
    compute_subject_allocations,
    calculate_total_study_hours,
    compute_available_time_blocks,
)
from utils import (
    parse_subjects_and_confidence,
    build_lifestyle_block,
    handle_file_upload,
    format_agent_output,
    validate_inputs,
    build_summary_card,
)
from state import StrategyMode


# ─────────────────────────────────────────────
# Core Agent Runner (called by Gradio)
# ─────────────────────────────────────────────

def generate_strategy(
    subjects_input: str,
    confidence_input: str,
    exam_date: str,
    daily_hours: float,
    # Lifestyle inputs
    wake_time: str,
    sleep_time: str,
    meal_slots_raw: str,
    routine_slots_raw: str,
    # Syllabus
    syllabus_text: str,
    file_upload,
):
    """
    Main handler called when user clicks 'Generate Strategy'.
    Yields progressive output for streaming feel.
    """
    # Sanitise ALL inputs — Gradio passes None for hidden components
    subjects_input    = subjects_input    or ""
    confidence_input  = confidence_input  or ""
    exam_date         = exam_date         or ""
    daily_hours       = float(daily_hours or 4.0)
    wake_time         = wake_time         or "07:00"
    sleep_time        = sleep_time        or "22:00"
    meal_slots_raw    = meal_slots_raw    or ""
    routine_slots_raw = routine_slots_raw or ""
    syllabus_text     = syllabus_text     or ""

    # ── Step 1: Validate ─────────────────────
    yield "⏳ Validating inputs...", "", ""

    is_valid, err = validate_inputs(subjects_input, exam_date, daily_hours)
    if not is_valid:
        yield err, "", ""
        return

    # ── Step 2: Parse Inputs ─────────────────
    yield "🧮 Analyzing subject priorities...", "", ""

    subjects_raw, confidence_scores = parse_subjects_and_confidence(
        subjects_input, confidence_input
    )

    # ── Step 3: Compute State ─────────────────
    days_remaining = calculate_days_remaining(exam_date)
    total_hours = calculate_total_study_hours(days_remaining, daily_hours)
    strategy_mode = determine_strategy_mode(days_remaining)
    subjects = compute_subject_allocations(subjects_raw, confidence_scores, total_hours)

    # Mode-aware lifestyle block
    is_intensive = strategy_mode == StrategyMode.INTENSIVE
    lifestyle = build_lifestyle_block(
        wake_time, sleep_time, meal_slots_raw, routine_slots_raw,
        intensive_mode=is_intensive
    )

    # ── Step 4: Build Summary Card ───────────
    summary = build_summary_card(subjects, days_remaining, total_hours, strategy_mode.value)

    mode_msg = (
        "🚨 **Intensive Revision Mode activated** — urgency detected!"
        if is_intensive
        else "📘 **Progressive Mastery Mode** — balanced preparation ahead."
    )

    yield f"🗂️ {mode_msg}\n\n{summary}", "", ""

    # ── Step 5: Handle File Upload ───────────
    syllabus_context = ""
    if file_upload is not None:
        yield f"🗂️ {mode_msg}\n\n{summary}", "📄 Parsing syllabus document...", ""
        syllabus_context = handle_file_upload(file_upload)
        if syllabus_context:
            syllabus_context = f"[Uploaded Syllabus Context]\n{syllabus_context}"

    # Merge with pasted text if both present
    if syllabus_text.strip() and not syllabus_context:
        syllabus_context = f"[Pasted Syllabus Context]\n{syllabus_text.strip()[:2000]}"
    elif syllabus_text.strip() and syllabus_context:
        syllabus_context += f"\n\n[Additional Context]\n{syllabus_text.strip()[:500]}"

    # ── Step 6: Run Agent ─────────────────────
    yield f"🗂️ {mode_msg}\n\n{summary}", "🤖 Agent reasoning... generating your strategy...", ""

    try:
        raw_output = run_agent(
            subjects_raw=subjects_raw,
            confidence_scores=confidence_scores,
            exam_date=exam_date,
            daily_study_hours=daily_hours,
            lifestyle=lifestyle,
            syllabus_context=syllabus_context if syllabus_context else None,
        )

        final_output = format_agent_output(raw_output, strategy_mode.value, days_remaining)

        yield (
            f"✅ **Strategy generated!** {mode_msg}\n\n{summary}",
            "✅ Complete!",
            final_output,
        )

    except Exception as e:
        yield (
            f"⚠️ Error: {str(e)}\n\nPlease check your inputs and try again.",
            "",
            "",
        )


# ─────────────────────────────────────────────
# Lifestyle Section Visibility Toggle
# ─────────────────────────────────────────────

def toggle_lifestyle_section(exam_date: str, daily_hours: float):
    """Show extended lifestyle customization only in intensive mode."""
    try:
        days = calculate_days_remaining(exam_date)
        mode = determine_strategy_mode(days)
        is_intensive = mode == StrategyMode.INTENSIVE
        label = (
            f"🚨 Intensive Revision Mode ({days} days) — Lifestyle Customization Unlocked"
            if is_intensive
            else f"📘 Progressive Mode ({days} days) — Standard Schedule"
        )
        return gr.update(visible=is_intensive), label
    except Exception:
        return gr.update(visible=False), "📅 Set exam date to detect strategy mode"


# ─────────────────────────────────────────────
# Gradio UI Construction
# ─────────────────────────────────────────────

CSS = """
.gradio-container { max-width: 1400px !important; font-family: 'Segoe UI', sans-serif; }
.title-header { text-align: center; padding: 20px 0 10px; }
.title-header h1 { font-size: 2em; font-weight: 700; color: #2d3748; }
.title-header p { color: #718096; font-size: 1em; }
.mode-badge { padding: 8px 16px; border-radius: 8px; font-weight: 600; }
.section-header { font-weight: 600; font-size: 1.1em; color: #4a5568; margin-bottom: 8px; }
#output-panel { background: #f7fafc; border-radius: 12px; padding: 16px; }
#summary-panel { background: #ebf8ff; border-radius: 10px; padding: 12px; }
footer { display: none !important; }
"""

def build_ui():
    with gr.Blocks(css=CSS, title="Exam Preparation Strategy Agent") as demo:

        # ── Header ──────────────────────────
        gr.HTML("""
        <div class="title-header">
            <h1>🎓 Exam Preparation Strategy Agent</h1>
            <p>A constraint-aware academic planning agent that converts your exam goals into optimized preparation strategies.</p>
        </div>
        """)

        with gr.Row():

            # ════════════════════════════════
            # LEFT PANEL — Inputs
            # ════════════════════════════════
            with gr.Column(scale=1, min_width=380):

                gr.Markdown("### 📚 Subjects & Confidence")

                subjects_input = gr.Textbox(
                    label="Subjects (comma-separated)",
                    placeholder="Math, Physics, Chemistry, Biology",
                    lines=2,
                    info="Enter all subjects you need to study."
                )

                confidence_input = gr.Textbox(
                    label="Confidence Scores (1–10 per subject)",
                    placeholder="Math:4, Physics:7, Chemistry:9  OR  4, 7, 9",
                    lines=1,
                    info="1–5 = High priority | 6–8 = Mid | 9–10 = Low. Lower score = more study time."
                )

                gr.Markdown("### 📅 Exam Details")

                with gr.Row():
                    exam_date = gr.Textbox(
                        label="Exam Date",
                        placeholder="YYYY-MM-DD",
                        info="Format: 2025-07-20"
                    )
                    daily_hours = gr.Slider(
                        label="Daily Study Hours",
                        minimum=1, maximum=12, value=4, step=0.5,
                        info="Hours available per day for studying."
                    )

                # Mode indicator
                mode_indicator = gr.Markdown(
                    "📅 *Set exam date to detect strategy mode*",
                    elem_id="mode-indicator"
                )

                # Auto-detect mode on date change
                exam_date.change(
                    fn=lambda d, h: toggle_lifestyle_section(d, h)[1],
                    inputs=[exam_date, daily_hours],
                    outputs=[mode_indicator]
                )

                gr.Markdown("### 🕐 Standard Schedule")

                with gr.Row():
                    wake_time = gr.Textbox(
                        label="Wake Time",
                        value="07:00",
                        placeholder="07:00"
                    )
                    sleep_time = gr.Textbox(
                        label="Sleep Time",
                        value="22:00",
                        placeholder="22:00"
                    )

                meal_slots = gr.Textbox(
                    label="Meal Slots (comma or newline separated)",
                    placeholder="08:00-08:30, 13:00-13:30, 19:00-19:30",
                    value="08:00-08:30, 13:00-13:30, 19:00-19:30",
                    lines=2
                )

                # Intensive-only lifestyle customization
                with gr.Group(visible=False) as intensive_lifestyle_group:
                    gr.Markdown("### 🚨 Intensive Mode — Custom Lifestyle")
                    gr.Markdown(
                        "*Only available in Intensive Revision Mode (≤5 days). "
                        "Override your routine to maximize revision time.*",
                        elem_classes=["section-header"]
                    )
                    routine_slots = gr.Textbox(
                        label="Routine Commitments (exercise, prayer, etc.)",
                        placeholder="06:30-07:00 (exercise), 07:30-08:00 (morning routine)",
                        lines=2,
                        info="These will be blocked off from study time."
                    )

                # Toggle intensive group on date change
                exam_date.change(
                    fn=lambda d, h: toggle_lifestyle_section(d, h)[0],
                    inputs=[exam_date, daily_hours],
                    outputs=[intensive_lifestyle_group]
                )

                # Default routine slots for non-intensive
                routine_slots_hidden = gr.Textbox(visible=False, value="")

                gr.Markdown("### 📄 Syllabus Context (Optional)")

                syllabus_text = gr.Textbox(
                    label="Paste Syllabus or Key Topics",
                    placeholder="Paste 1–2 paragraphs from your syllabus or a list of key topics...",
                    lines=4,
                    info="The agent will use this to refine your mini goals and topic focus."
                )

                file_upload = gr.File(
                    label="Or Upload Syllabus (.docx, max ~2 paragraphs)",
                    file_types=[".docx"],
                    type="filepath"
                )

                generate_btn = gr.Button(
                    "🚀 Generate My Strategy",
                    variant="primary",
                    size="lg"
                )

            # ════════════════════════════════
            # RIGHT PANEL — Outputs
            # ════════════════════════════════
            with gr.Column(scale=1, min_width=500):

                gr.Markdown("### 📊 Planning Analysis")
                summary_output = gr.Markdown(
                    value="*Your subject allocations and strategy mode will appear here...*",
                    elem_id="summary-panel"
                )

                gr.Markdown("### ⚙️ Agent Status")
                status_output = gr.Markdown(
                    value="*Waiting for input...*"
                )

                gr.Markdown("### 📋 Your Exam Strategy")
                plan_output = gr.Markdown(
                    value="*Your personalized exam strategy will be generated here...*",
                    elem_id="output-panel"
                )

        # ── Footer ──────────────────────────
        gr.HTML("""
        <div style="text-align:center; margin-top:20px; color:#a0aec0; font-size:0.85em;">
            🤖 Powered by Gemini 2.0 Flash + LangGraph &nbsp;|&nbsp;
            🧠 Constraint-Aware Academic Planning Agent
        </div>
        """)

        # ── Button Action ────────────────────
        generate_btn.click(
            fn=generate_strategy,
            inputs=[
                subjects_input,
                confidence_input,
                exam_date,
                daily_hours,
                wake_time,
                sleep_time,
                meal_slots,
                routine_slots,
                syllabus_text,
                file_upload,
            ],
            outputs=[summary_output, status_output, plan_output],
        )

    return demo


# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  🎓 Exam Preparation Strategy Agent")
    print("  Powered by Gemini 2.0 Flash + LangGraph")
    print("=" * 60)

    os.environ.setdefault("GROQ_API_KEY", "API_KEY_GOES_HERE")

    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
