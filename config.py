"""config.py — ScribeAI centralised configuration"""

APP_NAME     = "ScribeAI"
APP_VERSION  = "2.0"
APP_SUBTITLE = "Agentic Document Extraction System"
INSTITUTION  = "FAST-NUCES · BSAI · PPIT"
WINDOW_W, WINDOW_H = 1300, 820

OLLAMA_URL = "http://localhost:11434"

# ── Vision engines shown in the UI dropdown ───────────────────
# key  : internal id
# label: shown in UI
# type : "vision" (multimodal) | "ocr" (traditional)
# model: ollama model name (vision only)
ENGINES = [
    {"key": "minicpm-v",  "label": "MiniCPM-V  (best for handwriting)", "type": "vision",  "model": "minicpm-v"},
    {"key": "llava",      "label": "LLaVA 7B",                           "type": "vision",  "model": "llava:7b-v1.6"},
    {"key": "easyocr",    "label": "EasyOCR  (printed text)",            "type": "ocr",     "model": None},
    {"key": "tesseract",  "label": "Tesseract  (printed/typed)",         "type": "ocr",     "model": None},
    {"key": "paddleocr",  "label": "PaddleOCR  (high accuracy)",        "type": "ocr",     "model": None},
]
DEFAULT_ENGINE = "minicpm-v"

# ── Cleanup LLM (text post-processing) ───────────────────────
# Runs after extraction to fix spelling, format equations, remove repeats.
# Uses a text-only model — NOT the vision model.
CLEANUP_ENABLED = True
CLEANUP_MODEL   = "mistral:7b"   # change to any of your installed models
# Fallback order if primary not found:
CLEANUP_FALLBACKS = ["mistral:7b", "qwen2.5:7b", "llama3:8b", "hermes3:8b"]

# ── Agent behaviour ───────────────────────────────────────────
MAX_RETRIES          = 2     # fewer retries — cleanup LLM handles quality
QUALITY_THRESHOLD    = 0.55  # lower bar since cleanup fixes output
STREAM_TOKENS        = True
PREPROCESS_LEVEL     = "medium"   # "light" | "medium" | "heavy"
MAX_IMAGE_DIM        = 2048
OUTPUT_DIR           = "outputs"

# ── Pipeline stages ───────────────────────────────────────────
STAGES = [
    ("🔍", "Perception",   "Loading & preprocessing image"),
    ("🧠", "Extraction",   "Running OCR / vision model"),
    ("✅", "Validation",   "Scoring extraction quality"),
    ("✨", "Cleanup",      "LLM fixing spelling & equations"),
    ("📄", "Generation",   "Building DOCX + PDF"),
    ("💾", "Memory",       "Saving to agent memory"),
]

# ── Vision model prompts ──────────────────────────────────────
# NO inline examples — vision models copy them as output templates.
SYSTEM_PROMPT = (
    "You are an OCR assistant. "
    "Read the image and transcribe only the text you actually see in it. "
    "Do not repeat yourself. Do not invent content. Stop when you finish the image."
)

PROMPTS = {
    1: (
        "Transcribe all handwritten text in this image from top to bottom. "
        "Use ## for main headings, ### for sub-headings, - for bullets, "
        "wrap math in dollar signs, use pipe tables for any tables. "
        "Write only what is in the image. Stop after the last line."
    ),
    2: (
        "Read this handwritten image and write out every word and symbol you see. "
        "Format as Markdown. Do not repeat or invent anything. "
        "Stop after the last visible line."
    ),
    3: (
        "Transcribe this image word by word from top to bottom. "
        "Write only what is visually present. Stop at the final visible line."
    ),
}

# ── Cleanup LLM prompt ────────────────────────────────────────
CLEANUP_PROMPT = """You are a text cleanup assistant for OCR output of handwritten academic notes.

Fix the following issues in the text below:
1. Fix obvious spelling errors (e.g. "Acisorption" → "Adsorption", "alosobcile" → "adsorbate")
2. Fix chemical formulas (H2O → H₂O, CaCl2 → CaCl₂, Fe3+ → Fe³⁺, KMnO4 → KMnO₄)
3. Wrap mathematical expressions in $ signs ($\\Delta H = -ve$, $T_c = \\frac{8a}{27Rb}$)
4. Remove any repeated paragraphs or sentences (keep only the first occurrence)
5. Fix obvious OCR errors using scientific context
6. Preserve the original structure (headings, bullets, tables) exactly

IMPORTANT:
- Do NOT add any new content not present in the original
- Do NOT change the structure or reorder sections
- Do NOT add explanations or commentary
- Return ONLY the corrected text, nothing else

Text to fix:
"""
