"""
agent/core.py — ScribeAgent orchestrator (6-stage pipeline)

Stage 1  Perception   — validate + preprocess image
Stage 2  Extraction   — OCR engine (vision model or traditional)
Stage 3  Validation   — quality score + retry decision
Stage 4  Cleanup      — LLM fixes spelling/equations/duplicates
Stage 5  Generation   — DOCX + PDF
Stage 6  Memory       — persist ExtractionRecord
"""

import os, re, time
from datetime import datetime
from pathlib import Path

from agent.vision   import OllamaVision, get_engine, available_engines
from agent.cleanup  import CleanupAgent
from agent.parser   import ContentParser
from agent.memory   import AgentMemory, ExtractionRecord
from generators.docx_generator import DocxGenerator
from generators.pdf_generator  import PdfGenerator
from config import OUTPUT_DIR, ENGINES


class ScribeAgent:

    def __init__(self):
        self.cleanup  = CleanupAgent()
        self.parser   = ContentParser()
        self.memory   = AgentMemory()
        self.docx_gen = DocxGenerator()
        self.pdf_gen  = PdfGenerator()
        self._engine_key = "minicpm-v"   # default; UI updates this
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def set_engine(self, key: str):
        self._engine_key = key

    def get_engine_key(self) -> str:
        return self._engine_key

    # ── main pipeline ─────────────────────────────────────────
    def run(self, image_path, progress_cb=None, token_cb=None, stage_cb=None) -> dict:

        t0         = time.time()
        image_path = os.path.abspath(image_path)

        def _s(n, msg):
            if stage_cb:    stage_cb(n)
            if progress_cb: progress_cb(msg)

        try:
            # ── 1. Perception ──────────────────────────────────
            _s(0, "🔍 Perception — validating image")
            if not os.path.exists(image_path):
                return self._err(f"File not found: {image_path}")

            cached = self.memory.already_processed(image_path)
            if cached:
                _s(5, "💾 Memory — serving cached extraction")
                return {
                    "success": True, "text": cached.extracted_text,
                    "quality": {"score": cached.quality_score}, "stats": {},
                    "docx_path": cached.output_docx, "pdf_path": cached.output_pdf,
                    "processing_time": 0.0, "retry_count": 0,
                    "cached": True, "error": None,
                    "engine": self._engine_key, "cleanup_model": self.cleanup.model_name,
                }

            # ── 2+3. Extraction + Validation ───────────────────
            _s(1, f"🧠 Extraction — {self._engine_key}")
            engine, etype = get_engine(self._engine_key)

            if etype == "vision":
                # Find the ollama model name for this engine key
                model = next(
                    (e["model"] for e in ENGINES if e["key"] == self._engine_key),
                    "minicpm-v"
                )
                text, quality, retries = engine.extract(
                    image_path, model,
                    progress_cb=progress_cb, token_cb=token_cb)
            else:
                text, quality, retries = engine.extract(
                    image_path,
                    progress_cb=progress_cb, token_cb=token_cb)

            _s(2, f"✅ Validation — score {quality['score']:.0%}")

            if not text.strip():
                return self._err(
                    "Engine returned empty text.\n"
                    "Try: better image lighting, different engine, or check Ollama."
                )

            # ── 4. Cleanup ─────────────────────────────────────
            _s(3, f"✨ Cleanup — {self.cleanup.model_name}")
            cleaned_text = self.cleanup.clean(text, progress_cb=progress_cb)
            # Update quality score on cleaned text (usually improves)
            if etype == "vision":
                from agent.vision import OllamaVision as _V
                quality = _V._score(cleaned_text)

            # ── 5. Generation ──────────────────────────────────
            _s(4, "📄 Generation — building DOCX + PDF")
            title  = Path(image_path).stem.replace("_", " ").title()
            parsed = self.parser.parse(cleaned_text, title=title)

            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(image_path).stem)[:28]
            base = os.path.join(OUTPUT_DIR, f"{safe}_{ts}")

            docx_path = base + ".docx"
            pdf_path  = base + ".pdf"
            self.docx_gen.generate(parsed, docx_path)
            self.pdf_gen.generate(parsed, pdf_path)

            # ── 6. Memory ──────────────────────────────────────
            _s(5, "💾 Memory — saving extraction record")
            elapsed = round(time.time() - t0, 1)
            rec = ExtractionRecord(
                timestamp       = datetime.now().isoformat(),
                image_path      = image_path,
                image_name      = Path(image_path).name,
                extracted_text  = cleaned_text,
                quality_score   = quality["score"],
                word_count      = quality.get("word_count", len(cleaned_text.split())),
                equation_count  = quality.get("eq_count", 0),
                retry_count     = retries,
                processing_time = elapsed,
                output_docx     = docx_path,
                output_pdf      = pdf_path,
            )
            self.memory.store(rec)

            return {
                "success": True, "text": cleaned_text,
                "quality": quality, "stats": parsed.stats,
                "docx_path": docx_path, "pdf_path": pdf_path,
                "processing_time": elapsed, "retry_count": retries,
                "cached": False, "error": None,
                "engine": self._engine_key,
                "cleanup_model": self.cleanup.model_name,
            }

        except Exception as exc:
            return self._err(str(exc))

    def check_ready(self):
        return OllamaVision.check_connection()

    def session_stats(self):
        return self.memory.session_stats()

    def history(self):
        return self.memory.all_history()

    def get_available_engines(self):
        return available_engines()

    @staticmethod
    def _err(msg):
        return {
            "success": False, "text": "", "error": msg,
            "quality": {"score": 0}, "stats": {},
            "docx_path": None, "pdf_path": None,
            "processing_time": 0, "retry_count": 0,
            "cached": False, "engine": "", "cleanup_model": "",
        }
