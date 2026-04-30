"""
agent/memory.py
Dual-layer agent memory.

Short-term : Python list in RAM (current session only)
Long-term  : JSON file on disk (persists across restarts)

The agent uses memory to:
  1. Skip re-processing the same image in one session
  2. Populate the History panel in the UI
  3. Compute aggregate session statistics
"""

import json, os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ExtractionRecord:
    timestamp:        str
    image_path:       str
    image_name:       str
    extracted_text:   str
    quality_score:    float     # 0.0 – 1.0
    word_count:       int
    equation_count:   int
    retry_count:      int
    processing_time:  float     # seconds
    output_docx:      Optional[str] = None
    output_pdf:       Optional[str] = None


class AgentMemory:
    _FILE = "agent_memory.json"

    def __init__(self):
        self.short_term: list[ExtractionRecord] = []   # RAM
        self.long_term:  list[dict]             = []   # disk
        self._load()

    # ── write ────────────────────────────────────────────────
    def store(self, rec: ExtractionRecord) -> None:
        self.short_term.append(rec)
        self.long_term.append(asdict(rec))
        self._save()

    # ── read ─────────────────────────────────────────────────
    def already_processed(self, image_path: str) -> Optional[ExtractionRecord]:
        """Return cached record if this image was processed this session."""
        norm = os.path.abspath(image_path)
        for rec in reversed(self.short_term):
            if os.path.abspath(rec.image_path) == norm:
                return rec
        return None

    def session_stats(self) -> dict:
        if not self.short_term:
            return {"processed": 0, "avg_quality": 0.0,
                    "total_words": 0, "total_eqs": 0, "avg_time": 0.0}
        qs = [r.quality_score for r in self.short_term]
        return {
            "processed":   len(self.short_term),
            "avg_quality": round(sum(qs) / len(qs), 3),
            "total_words": sum(r.word_count     for r in self.short_term),
            "total_eqs":   sum(r.equation_count for r in self.short_term),
            "avg_time":    round(
                sum(r.processing_time for r in self.short_term) / len(self.short_term), 1),
        }

    def all_history(self) -> list[dict]:
        """Newest first."""
        return list(reversed(self.long_term))

    # ── persistence ──────────────────────────────────────────
    def _load(self):
        if os.path.exists(self._FILE):
            try:
                with open(self._FILE, encoding="utf-8") as f:
                    self.long_term = json.load(f)
            except Exception:
                self.long_term = []

    def _save(self):
        try:
            with open(self._FILE, "w", encoding="utf-8") as f:
                json.dump(self.long_term, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # non-fatal
