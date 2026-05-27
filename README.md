# 🎓 Exam Preparation Strategy Agent

> A constraint-aware, behavior-sensitive academic planning agent that converts a student's exam goals into an optimized, adaptive preparation strategy.

---

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│              Gradio UI + App Orchestration              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                      workflow.py                        │
│         LangGraph Graph: START → Preprocess → Plan      │
└────────────────────────┬────────────────────────────────┘
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
┌────────────────────┐   ┌───────────────────────────────┐
│     tools.py       │   │          agent.py             │
│  Deterministic     │   │   Gemini LLM Reasoning Layer  │
│  - Days remaining  │   │   - Strategy explanation      │
│  - Hour weighting  │   │   - Timetable generation      │
│  - Time blocks     │   │   - Mini goals (edu + fun)    │
│  - .docx parsing   │   │   - Motivation line           │
└────────────────────┘   └───────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                       state.py                          │
│         TypedDict Schema + System Prompt                │
└─────────────────────────────────────────────────────────┘
```

**Key Design Principle:**
- 🐍 **Deterministic math** → `tools.py` (Python)
- 🤖 **Strategic reasoning** → `agent.py` (Gemini LLM)
- 🔄 **Flow control** → `workflow.py` (LangGraph)
- 🖥️ **Presentation** → `main.py` (Gradio)

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **Confidence Weighting** | 1–5 = High Priority (1.5x time), 6–8 = Mid (1.0x), 9–10 = Low (0.7x) |
| **Strategy Modes** | Progressive Mastery (>5 days) vs Intensive Revision (≤5 days) |
| **Lifestyle-Aware** | Wake/sleep times, meals, and routines carved out of schedule |
| **Intensive Customization** | Extra routine override available only in Intensive Mode |
| **Mini Goals** | Alternating educational + fun goals per study block |
| **Syllabus Context** | Optional .docx upload or paste — enriches topic mini goals |
| **Adaptive Planning** | Mode switches automatically based on days remaining |
| **PDF Export** | Export generated strategy to a PDF for easier consultation |

---

## 📁 File Structure

```
exam_prep_agent/
├── main.py          # Gradio UI + orchestration
├── agent.py         # Gemini LLM wrapper + prompt engineering
├── tools.py         # Deterministic computations (pure Python)
├── state.py         # TypedDict schema + system prompt
├── workflow.py      # LangGraph graph definition
├── utils.py         # UI helpers + input parsing
├── pdf_export.py    # Generated Strategy to PDF Export
├── run_with_pdf.py  # Updated Gradio UI for pdf export utilizes existing main.py
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Install Dependencies

```bash
pip install langgraph langchain-groq langchain-google-genai gradio python-docx python-dotenv
```

### 2. Run the App

```bash
python 
```

### 3. Open in Browser

```
http://localhost:7860
```

---

## 🎮 Demo Input Example

| Field | Example Value |
|-------|---------------|
| Subjects | `Math, Physics, Chemistry` |
| Confidence | `Math:3, Physics:6, Chemistry:9` |
| Exam Date | `2025-07-25` (adjust to future date) |
| Daily Hours | `5` |
| Wake Time | `06:30` |
| Sleep Time | `23:00` |

---

## 🔧 Configuration

API key is set directly in `agent.py`. To use `.env` instead:

```bash
# .env
GROQ_API_KEY=your_key_here
```

Then in `agent.py`, the `os.environ.get()` call picks it up automatically.

---

## 🎤 Demo Framing

> *"The agent functions as a constraint-aware academic execution planner. It evaluates available preparation time, analyzes subject mastery gaps, selects an optimal strategy mode, and generates a time-optimized execution plan with behavioral mini goals — all within a structured LangGraph pipeline."*

---

## ⚠️ Scope Boundaries (By Design)

This agent intentionally does NOT include:
- ❌ Dynamic rescheduling after missed days
- ❌ Calendar sync / persistent storage
- ❌ Authentication
- ❌ Multi-session tracking

These are excluded to maintain hackathon-grade reliability.
Controlled scope = controlled quality.

## 🧪 Design Decisions
> Deterministic vs LLM split

 Scheduling is intentionally non-LLM to avoid:

  - Hallucinated time allocation
  - Inconsistent outputs across runs
  - Non-reproducible behavior
  - LangGraph usage

> Chosen over linear chains because:

  - Planning is inherently stateful
  - Enables future revision loops
  - Improves observability of transitions
  - Confidence weighting system

> Maps subjective user input into structured planning logic:

  - High confidence → reinforcement efficiency bias
  - Low confidence → increased allocation weight

## ⚠️ Known Limitations
- No persistent memory across sessions
- No calendar integration or external syncing
- LLM output variability in explanations
- Extreme constraint inputs reduce optimization quality

Mitigation: deterministic core guarantees structural stability.

## 🧠 System Summary

This system is intentionally designed as:

A deterministic planning engine with an LLM-powered explanation layer.

Not:

A prompt-based AI scheduler.
