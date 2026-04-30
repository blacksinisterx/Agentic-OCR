# ScribeAI — Agentic OCR System
### FAST-NUCES · BSAI · Professional Practices in IT
### Phase 1 + Phase 2: Fully Local, GPU-Accelerated, Agentic Document Extraction

---

## 🎯 What This Project Actually Does (That Phase 1 Didn't)

| Capability | Phase 1 (Tesseract) | Phase 2 ScribeAI |
|---|---|---|
| Handwriting | ❌ Fails badly | ✅ Excellent |
| Chemistry equations | ❌ Garbled symbols | ✅ Correct LaTeX/Unicode |
| Diagrams | ❌ Not detected | ✅ Described structurally |
| Greek letters α β γ | ❌ Random chars | ✅ Correct |
| Subscripts H₂O | ❌ H2O | ✅ H₂O |
| Self-correction | ❌ One-shot | ✅ Retry loop |
| Memory of past runs | ❌ None | ✅ Session + persistent |
| Agent autonomy | ❌ Static tool | ✅ Goal-driven pipeline |
| Cost | Free | ✅ 100% Free (local) |

---

## 🖥️ Your Hardware & Model Selection

### Your Specs
- **GPU:** NVIDIA RTX 3050 Laptop — 4 GB VRAM dedicated + 15.8 GB shared
- **CPU:** Intel i7-12650H — 10 cores / 16 threads
- **Max download:** 8 GB

### Recommended Ollama Models (pick ONE primary)

| Model | Size | VRAM Used | Speed | Accuracy | Verdict |
|---|---|---|---|---|---|
| `llava:7b-v1.6` | 4.7 GB | ~4.5 GB VRAM | ~4 tok/s | ⭐⭐⭐⭐⭐ | **good** |
| `minicpm-v` | 5.5 GB | ~4 GB + shared | ~3 tok/s | ⭐⭐⭐⭐⭐ | **great for handwriting** |

> **Why `llava:7b-v1.6`?**  
> It will use 4 GB dedicated + ~0.5 GB shared VRAM. Windows allows this overflow automatically.  
> It understands scientific notation, chemical formulas, and handwriting far better than smaller models.  
> Per-page processing: ~90–150 seconds (acceptable for a student tool).

---

## 📁 Project Structure

```
ocr_agent/
│
├── README.md                    ← This file
├── requirements.txt             ← Python dependencies
├── config.py                    ← All settings (model, prompts, colors)
├── main.py                      ← Launch point — starts the GUI
│
├── agent/
│   ├── __init__.py
│   ├── core.py                  ← Orchestrator — runs the full pipeline
│   ├── vision.py                ← Ollama LLaVA interface (the AI brain)
│   ├── parser.py                ← Markdown → structured content tree
│   └── memory.py                ← Short-term + long-term memory
│
├── generators/
│   ├── __init__.py
│   ├── docx_generator.py        ← Produces formatted .docx
│   └── pdf_generator.py         ← Produces formatted .pdf (via reportlab)
│
├── utils/
│   ├── __init__.py
│   └── image_processor.py       ← OpenCV preprocessing pipeline
│
└── ui/
    ├── __init__.py
    ├── app.py                   ← Main CustomTkinter application window
    ├── panels.py                ← Reusable UI panels (preview, history, stats)
    └── styles.py                ← Theme constants
```

---

## ⚙️ Installation — Step by Step

### Step 1 — Install Ollama

Download from **https://ollama.com/download** → Windows installer  
After install, open PowerShell and verify:
```powershell
ollama --version
```

### Step 2 — Pull the Vision Model

```powershell
# Primary recommendation (4.7 GB download):
ollama pull llava:7b-v1.6

# If internet is slow, use lighter model (2.9 GB):
ollama pull llava-phi3
```

This downloads once and is stored locally forever. No internet needed after.

### Step 3 — Verify Model Works

```powershell
ollama run llava:7b-v1.6 "describe yourself in one sentence"
# Should reply: "I am a multimodal AI model..."
# Press Ctrl+D to exit
```

### Step 4 — Python Environment

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5 — Run ScribeAI

```powershell
python main.py
```

---

## 📦 requirements.txt

```
customtkinter>=5.2.2
CTkMessagebox>=2.7
python-docx>=1.1.0
reportlab>=4.1.0
Pillow>=10.3.0
opencv-python>=4.9.0
requests>=2.31.0
```

> **No GPU libraries needed** — Ollama handles GPU acceleration internally via CUDA.  
> All packages above are CPU-only Python packages, very lightweight.

---

## 🧠 Agentic System Design (Phase 2 Core)

### What Makes This "Agentic"?

A traditional OCR tool (Phase 1) is a **passive function**:
```
Image → Tesseract → Text (done, no matter how bad the result)
```

ScribeAI is an **autonomous agent** with a perception-decision-action-feedback loop:

```
┌─────────────────────────────────────────────────────────────┐
│                    SCRIBEAI AGENT LOOP                      │
│                                                             │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────────┐   │
│  │PERCEPTION│───▶│ INTELLIGENCE│───▶│     ACTION      │   │
│  │          │    │             │    │                 │   │
│  │Load image│    │LLaVA Vision │    │Generate DOCX/   │   │
│  │Preprocess│    │Understand   │    │PDF output       │   │
│  │Enhance   │    │& Extract    │    │Store to memory  │   │
│  └──────────┘    └──────┬──────┘    └────────┬────────┘   │
│                         │                    │             │
│                  ┌──────▼──────┐    ┌────────▼────────┐   │
│                  │  VALIDATION │    │    LEARNING     │   │
│                  │             │    │                 │   │
│                  │Quality check│    │Update session   │   │
│                  │Score < 0.6? │    │memory & history │   │
│                  │→ Retry loop │    │Track patterns   │   │
│                  └─────────────┘    └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Agent Pipeline Stages

```
Stage 1 — PERCEPTION
  └─ Load image (PIL)
  └─ Detect orientation, brightness, contrast
  └─ Apply adaptive preprocessing (deskew, denoise, enhance)
  └─ Resize for optimal model input

Stage 2 — INTELLIGENCE  
  └─ Send image + crafted prompt to LLaVA via Ollama API
  └─ Stream tokens as they're generated (live display)
  └─ Receive full markdown extraction

Stage 3 — VALIDATION (Self-Assessment Loop)
  └─ Count equations detected
  └─ Check structural completeness
  └─ Score: completeness, equation_accuracy, structure
  └─ If score < threshold → retry with stronger prompt
  └─ Max 3 retries, then accept best attempt

Stage 4 — PARSING
  └─ Markdown → structured content tree
  └─ Identify: headings, paragraphs, bullets, equations, diagrams
  └─ Inline analysis: bold, italic, equations, chemical formulas

Stage 5 — GENERATION
  └─ Walk content tree
  └─ Write .docx with proper styles, headings, equations
  └─ Write .pdf with ReportLab

Stage 6 — MEMORY
  └─ Store ExtractionRecord (path, text, quality, timing)
  └─ Persist to agent_memory.json
  └─ Update session statistics in UI
```

### Memory Architecture

```python
# Short-term memory: current session
self.session_memory: list[ExtractionRecord]

# Long-term memory: persistent across restarts
# Stored in: agent_memory.json
self.long_term_memory: list[dict]
```

The agent uses memory to:
1. Avoid re-processing the same image in the same session
2. Track quality trends (is the model getting better results over time?)
3. Display history panel in the UI

---

## 🎨 UI Design

The app uses **CustomTkinter** (modern dark-theme Tkinter wrapper):

```
┌─────────────────────────────────────────────────────────────────┐
│  🔬 ScribeAI — Agentic OCR System              [_] [□] [×]     │
├──────────────┬──────────────────────────────────────────────────┤
│              │  ┌─ AGENT PIPELINE STATUS ──────────────────┐   │
│  📁 Drop     │  │ ✅ Perception   — Image loaded            │   │
│  image here  │  │ 🔄 Intelligence — Extracting...          │   │
│              │  │ ⏳ Validation   — Waiting                │   │
│  [Select     │  └───────────────────────────────────────────┘   │
│   Image]     │                                                   │
│              │  ┌─ EXTRACTED TEXT ──────────────────────────┐  │
│  ──────────  │  │ ## SURFACE CHEMISTRY                      │  │
│  Preview     │  │ **Adsorption**: Accumulation of...        │  │
│  thumbnail   │  │ - Enthalpy (ΔH) = −ve (exothermic)       │  │
│              │  │ - Entropy (ΔS) = −ve                      │  │
│  ──────────  │  │ $\Delta H > T\Delta S$                    │  │
│  STATS:      │  └───────────────────────────────────────────┘  │
│  Words: 847  │                                                   │
│  Eqs:   23   │  [Export DOCX]  [Export PDF]  [Copy Text]       │
│  Quality:9.1 │                                                   │
├──────────────┴──────────────────────────────────────────────────┤
│  📊 Session: 3 images · 2,341 words · Avg quality 8.9/10       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📄 DOCX Output Format

The generated Word document includes:
- **Title** in large bold heading style
- **Section headings** (H1 → H2 → H3) with proper heading styles (navigable in Word)
- **Bullet lists** using Word's native list styles
- **Equations** rendered inline using Unicode + LaTeX notation
- **Boxed content** using Word bordered paragraphs  
- **Diagram descriptions** in styled callout boxes
- **Metadata footer**: extraction date, quality score, image source

The document is **fully editable** — every paragraph, equation, and heading can be edited directly in Microsoft Word or LibreOffice.

---

## 📄 PDF Output Format

Generated with ReportLab:
- Professional academic formatting
- Proper heading hierarchy
- Equations in monospace with boxes
- Page numbers, header with app name
- Diagram description boxes with border

---

## 🔧 config.py — Key Settings to Customize

```python
# Change model here (if you pulled a different one)
OLLAMA_MODEL = "llava:7b-v1.6"     # or "llava-phi3"
OLLAMA_URL   = "http://localhost:11434"

# Quality threshold — 0.0 to 1.0
# Lower = accept faster (less accurate), Higher = more retries (slower)
CONFIDENCE_THRESHOLD = 0.65

# Max retries before accepting best result
MAX_RETRIES = 3

# Preprocessing intensity
# "light"  = just resize (fast, good images)
# "medium" = denoise + contrast (recommended)
# "heavy"  = full adaptive thresholding (slow, low quality scans)
PREPROCESS_LEVEL = "medium"
```

---

## ⚗️ OCR Prompt Engineering

The most important part of making LLaVA work well for chemistry notes is the prompt.  
ScribeAI uses a **layered prompt strategy**:

### Attempt 1 — Standard extraction
```
You are ScribeAI, an expert in extracting handwritten academic notes...
[system instructions]
Extract ALL content from this image as structured markdown.
```

### Attempt 2 — Equation emphasis (if quality low)
```
[previous prompt]
IMPORTANT: Pay extra attention to all mathematical equations, 
chemical formulas, and Greek letters. 
Double-check every subscript and superscript.
```

### Attempt 3 — Maximum fidelity
```
[previous prompt]
CRITICAL FINAL ATTEMPT: Extract EVERYTHING visible, no matter how 
small or faint. All arrows (→, ⇌), subscripts (H₂O, CaCl₂), 
and equations must appear correctly.
```

Each attempt produces output that is quality-scored. The best attempt wins.

---

## 🏗️ Phase 2 Requirements Mapping

| Requirement (from spec) | ScribeAI Implementation |
|---|---|
| Perception, Decision, Action, Learning | 6-stage pipeline in `agent/core.py` |
| Memory (short + long term) | `agent/memory.py` — session RAM + JSON disk |
| Goal-based agent | Retries until quality threshold met |
| External tools | Ollama API, OpenCV, python-docx, ReportLab |
| Human-in-the-loop | Manual trigger, preview before export |
| Autonomy level | Semi-autonomous (triggers manual, runs fully) |
| Ethical agent design | Local processing = no data leaves machine |
| Risk assessment | Retry cap, fallback model, quality logging |
| Safety mechanisms | Logging of all extractions, quality score displayed |

---

## 🚀 Running the App

```powershell
# Make sure Ollama is running (it starts automatically after install)
# If not, start it:
ollama serve

# In another terminal, activate venv and run:
.\venv\Scripts\activate
python main.py
```

---

## 🐞 Troubleshooting

| Problem | Solution |
|---|---|
| `Connection refused` on port 11434 | Run `ollama serve` in a terminal first |
| Very slow extraction | Normal — LLaVA 7B takes 90-150s/page on 3050 |
| Out of VRAM error | Switch to `llava-phi3` in config.py |
| Poor equation extraction | Ensure image is well-lit; use "heavy" preprocessing |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in venv |
| Blurry output image | Increase image resolution before scanning |

---

## 📚 Academic Integrity Note

All OCR processing runs **100% locally on your machine**.  
No images, text, or personal data is sent to any external server.  
This satisfies the privacy requirements discussed in Phase 2 (CLO 6 — Data Protection).

---

*ScribeAI — Built with ❤️ for FAST-NUCES PPIT Course*  
*Phase 2: Agentic Transformation — Professional Practices in IT*
