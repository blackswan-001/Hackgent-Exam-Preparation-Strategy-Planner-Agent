"""
run_with_pdf.py — Alternative entrypoint that adds PDF export to the
Exam Preparation Strategy Agent WITHOUT modifying any existing file.

Usage:
    python run_with_pdf.py

This replaces running main.py directly when you want PDF export.
main.py, agent.py, tools.py, utils.py, state.py, workflow.py — untouched.
"""

import os
import re
import gradio as gr

# ── Import the existing UI builder (zero modifications) ──────────────────────
from main import build_ui
from pdf_export import export_strategy_to_pdf

os.environ.setdefault("GROQ_API_KEY", "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")


# ─────────────────────────────────────────────
# PDF Export Handler
# ─────────────────────────────────────────────

def handle_pdf_export(plan_markdown: str, summary_markdown: str):
    """
    Read the current plan and summary outputs and generate a PDF.
    Called when the user clicks the Export button.
    """
    plan_markdown   = plan_markdown   or ""
    summary_markdown = summary_markdown or ""

    # Nothing generated yet
    if not plan_markdown.strip() or "will be generated here" in plan_markdown:
        return gr.update(value=None, visible=False)

    # Extract days remaining from summary card
    days = 0
    days_match = re.search(r"\*\*Days Remaining:\*\*\s*(\d+)", summary_markdown)
    if days_match:
        days = int(days_match.group(1))

    # Extract strategy mode from summary card
    mode = "Progressive Mastery Mode"
    mode_match = re.search(r"\*\*Strategy Mode:\*\*\s*(.+)", summary_markdown)
    if mode_match:
        mode = mode_match.group(1).strip()

    try:
        pdf_path = export_strategy_to_pdf(plan_markdown, days, mode)
        print(f"[run_with_pdf] PDF ready: {pdf_path}")
        return gr.update(value=pdf_path, visible=True)
    except Exception as e:
        print(f"[run_with_pdf] PDF export failed: {e}")
        return gr.update(value=None, visible=False)


# ─────────────────────────────────────────────
# Build Extended UI
# ─────────────────────────────────────────────

def build_extended_ui():
    """
    Build the original UI, then append the PDF export row inside the
    same Blocks context — no changes to main.py required.
    """
    demo = build_ui()   # original UI, fully intact

    with demo:          # re-enter the same Blocks context to extend it
        gr.Markdown("---")

        with gr.Row():
            with gr.Column(scale=1):
                pass    # left column spacer — keeps button on the right side

            with gr.Column(scale=1):
                gr.Markdown("### 📄 Export")
                export_btn = gr.Button(
                    "📥 Download Strategy as PDF",
                    variant="primary",
                    size="lg",
                )
                pdf_file = gr.File(
                    label="Your PDF is ready — click to download",
                    visible=False,
                    interactive=False,
                )

        # Wire the button to the export handler.
        # Reads plan_output and summary_output that already exist in the demo.
        # We identify them by finding the Markdown components in the demo.
        plan_component    = None
        summary_component = None

        for component in demo.blocks.values():
            if isinstance(component, gr.Markdown):
                if hasattr(component, 'elem_id'):
                    if component.elem_id == "output-panel":
                        plan_component = component
                    elif component.elem_id == "summary-panel":
                        summary_component = component

        # Fallback: locate by position if elem_id lookup fails
        if plan_component is None or summary_component is None:
            markdown_components = [
                c for c in demo.blocks.values()
                if isinstance(c, gr.Markdown)
            ]
            # summary is the 4th markdown (after header HTML, section labels)
            # plan is the 5th markdown output
            output_markdowns = [
                c for c in markdown_components
                if c.value and (
                    "will be generated here" in str(c.value) or
                    "allocations" in str(c.value).lower() or
                    "waiting" in str(c.value).lower()
                )
            ]
            if len(output_markdowns) >= 2:
                summary_component = output_markdowns[0]
                plan_component    = output_markdowns[1]

        if plan_component and summary_component:
            export_btn.click(
                fn=handle_pdf_export,
                inputs=[plan_component, summary_component],
                outputs=[pdf_file],
            )
        else:
            # Absolute fallback — just use State approach
            plan_state    = gr.State("")
            summary_state = gr.State("")
            export_btn.click(
                fn=handle_pdf_export,
                inputs=[plan_state, summary_state],
                outputs=[pdf_file],
            )
            print("[run_with_pdf] Warning: could not auto-locate output components. "
                  "PDF will export empty plan — ensure strategy is generated first.")

    return demo


# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Exam Preparation Strategy Agent  +  PDF Export")
    print("  Run: python run_with_pdf.py")
    print("=" * 60)

    app = build_extended_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
