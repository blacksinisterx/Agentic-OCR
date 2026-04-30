# ScribeAI — Agentic Document Extraction System
### FAST-NUCES · BSAI · Professional Practices in IT
### Phase 1 + Phase 2: Fully Local, Agentic Document Extraction & OCR Pipeline

---

## 🎯 What This Project Actually Does (That Phase 1 Didn't)

| Capability | Phase 1 (Tesseract) | Phase 2 ScribeAI |
|---|---|---|
| Handwriting | ❌ Fails badly | ✅ Excellent |
| Chemistry equations | ❌ Garbled symbols | ✅ Correct LaTeX/Unicode |
| Diagrams | ❌ Not detected | ✅ Described structurally |
| Greek letters α β γ | ❌ Random chars | ✅ Correct |
| Subscripts H₂O | ❌ H2O | ✅ H₂O |
| Self-correction | ❌ One-shot | ✅ Validation & LLM Cleanup Pass |
| Memory of past runs | ❌ None | ✅ Session + Persistent file tracking |
| Agent autonomy | ❌ Static tool | ✅ Goal-driven pipeline |
| Cost | Free | ✅ 100% Free (local) |

---

## 🖥️ Recommended AI Models

ScribeAI utilizes *two* categories of models in tandem to guarantee perfectly formatted Markdown and structurally sound representations of your handwritten pages:

**1. Vision Models (Extraction)**
*This relies on Ollama embeddings pulling meaning directly out of standard or complex images.*
| Model | Type | Speed | Verdict |
|---|---|---|---|
| `minicpm-v` | Vision | ~3 tok/s | **✅ BEST FOR HANDWRITING (Default)** |
| `llava:7b-v1.6` | Vision | ~4 tok/s | Excellent alternative |

**2. Language Models (Cleanup & Repair)**
*Takes raw OCR/Vision output and corrects chemical/math structures, removes repetitions, and fixes hallucinations.*
| Model | Type | Speed | Verdict |
|---|---|---|---|
| `mistral:7b` | Text | ~15 tok/s | **✅ BEST FOR CLEANUP (Default)** |
| `qwen2.5:7b` | Text | ~18 tok/s | Fast & accurate |

**Standard OCR Engines Supported**
- **EasyOCR** (Best for printed text)
- **Tesseract** (Traditional print fallback)
- **PaddleOCR** (Accuracy on multiline text reading)

> **Note on VRAM:** Running both a vision and text model sequentially will comfortably fit within modern system shared/dedicated memory arrays. ScribeAI limits concurrent memory overheads using cleanup fallbacks seamlessly.

---

## 📁 Project Structure

```text
scribeai/
│
├── README.md                    ← This file
├── requirements.txt             ← Python dependencies
├── config.py                    ← Configuration map (models, thresholds, UI themes)
├── main.py                      ← Launch point — Starts the full PyQt6 GUI
├── agent_memory.json            ← Persistent memory storage of extraced pages
│
├── agent/
│   ├── __init__.py
│   ├── core.py                  ← Orchestrator tracking perception, intelligence, validation loops
│   ├── vision.py                ← Connects to Ollama Multi-Modal LLMs (OCR engine switchers)
│   ├── cleanup.py               ← Fallback LLM Cleanup mechanism to remove redundancies
│   ├── parser.py                ← Markdown → structured content tree formatting
│   └── memory.py                ← Short-term + Long-term pipeline memory processing
│
├── generators/
│   ├── docx_generator.py        ← Produces neatly formatted .docx structures
│   └── pdf_generator.py         ← Produces formatted .pdf outputs (via reportlab)
│
├── utils/
│   └── image_processor.py       ← OpenCV active visual preprocessing tools
│
└── ui/
    ├── main_window.py           ← Main PyQt6 application architecture
    ├── worker.py                ← Multi-threaded PyQt6 workers ensuring non-blocking states
    └── styles/
        └── dark.qss             ← QSS Stylesheets for PyQt6 app theme
```

---

## ⚙️ Installation — Step by Step

### Step 1 — Install Ollama

Download from **https://ollama.com/download** → Windows installer  
After install, open PowerShell and verify:
```powershell
ollama --version
```

### Step 2 — Pull the Default Models

```powershell
# Pull the default vision model:
ollama pull minicpm-v

# Pull the default cleanup text model:
ollama pull mistral:7b
```

### Step 3 — Python Setup & Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies needed by PyQt6 GUI and report generators
pip install -r requirements.txt
```

### Step 4 — Run ScribeAI

```powershell
python main.py
```

---

## 📦 requirements.txt Breakdown

```text
PyQt6>=6.6.0
python-docx>=1.1.0
reportlab>=4.1.0
Pillow>=10.3.0
opencv-python>=4.9.0
requests>=2.31.0
```

> **No GPU Python libraries needed** — GPU bindings are internal to Ollama via CUDA. Your machine avoids colossal footprint `torch` bindings.

---

## 🧠 ScribeAI Agentic Architecture

Traditional pipelines passively push data across. ScribeAI operates an active perception validation node:

### 1. PERCEPTION
- Load standard `PIL` images.
- Dynamically detect orientation, denoise, adjust light threshold, and extract edge boxes via OpenCV matching `PREPROCESS_LEVEL`.

### 2. EXTRACTION (Intelligence)
- Supply adaptive instruction templates to `MiniCPM-V` or `LLaVa` to grab tables, formatting, math blocks, and equations.
- Stream generation blocks instantly displaying via PyQt signal slots.

### 3. VALIDATION
- Evaluate extraction vs repetition penalties.
- Score against target rules (Did it find equations?). If `Score < 0.55`, dynamically step-up prompting aggressiveness up to `MAX_RETRIES`.

### 4. CLEANUP (Self-Correction)
- Hand raw vision texts automatically directly to `mistral:7b`.
- Resolve common parsing artifacts (`alonsobcile` → `adsorbate`).
- Inject missing `$LaTeX$` parameters into physical formulae automatically.

### 5. GENERATION
- Assemble parsed text maps identifying bold/italics.
- Transpile into Word templates pushing out `ReportLab` native PDFs and native `DOCX`.

### 6. MEMORY
- Prevent continuous repeat processing by storing file metadata states in memory maps natively mapped across sessions into `agent_memory.json`.

---

## 🎨 UI Interface

```text
┌─────────────────────────────────────────────────────────────┐
│  🔬 ScribeAI — Agentic Document Extraction        [_] [□] [×]│
├──────────────┬──────────────────────────────────────────────┤
│              │  ┌─ AGENT PIPELINE STATUS ───────────────┐   │
│  📁 Drop     │  │ ✅ Perception   — Image loaded        │   │
│  image here  │  │ 🔄 Extraction   — Running model...    │   │
│              │  │ ⏳ Cleanup      — Waiting             │   │
│  [Select     │  └───────────────────────────────────────┘   │
│   Image]     │                                              │
│              │  ┌─ EXTRACTED TEXT ──────────────────────┐   │
│  ──────────  │  │ ## SURFACE CHEMISTRY                  │   │
│  Preview     │  │ - Enthalpy (ΔH) = −ve (exothermic)    │   │
│  thumbnail   │  │ $\Delta H > T\Delta S$                  │   │
│  ──────────  │  └───────────────────────────────────────┘   │
│              │                                              │
│  Engine Drop │  [Export DOCX]  [Export PDF]  [Copy Text]    │
├──────────────┴──────────────────────────────────────────────┤
│  📊 Ready...                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 config.py — Key Settings

Modify how ScribeAI runs globally via simple constants:

```python
# System Vision defaults (MiniCPM-V heavily favored for Handwriting accuracy)
DEFAULT_ENGINE = "minicpm-v"

# Intelligent Editor LLM defaults
CLEANUP_ENABLED = True
CLEANUP_MODEL   = "mistral:7b" 

# Base quality thresholds out of a perfect 1.0 (forces retry loops)
QUALITY_THRESHOLD = 0.55

# Retries afforded before pushing to Cleanup sequence
MAX_RETRIES = 2

# Global file Pre-processing (None, Light, Medium, Heavy)
PREPROCESS_LEVEL = "medium"
```