"""
agent/cleanup.py
LLM post-processor — fixes spelling, formats equations, removes duplicates.

Uses a text-only model (mistral:7b, qwen2.5, etc.) via Ollama /api/chat.
Runs AFTER extraction as pipeline Stage 4.
"""

import json, requests, re
from config import OLLAMA_URL, CLEANUP_MODEL, CLEANUP_FALLBACKS, CLEANUP_PROMPT


class CleanupAgent:
    """Runs the cleanup LLM and returns corrected text."""

    def __init__(self):
        self._model = self._find_model()

    # ── find available model ──────────────────────────────────
    def _find_model(self) -> str | None:
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=4)
            names = [m["name"] for m in r.json().get("models", [])]
            # Try primary, then fallbacks
            for candidate in [CLEANUP_MODEL] + CLEANUP_FALLBACKS:
                base = candidate.split(":")[0]
                if any(base in n for n in names):
                    return candidate
        except Exception:
            pass
        return None

    @property
    def model_name(self) -> str:
        return self._model or "none"

    @property
    def available(self) -> bool:
        return self._model is not None

    # ── main entry ────────────────────────────────────────────
    def clean(self, text: str, progress_cb=None) -> str:
        """
        Send text to the cleanup LLM and return corrected version.
        Falls back to heuristic-only cleanup if no model available.
        """
        if progress_cb:
            progress_cb(f"✨ Cleanup — {self._model or 'heuristic only'}")

        if not self._model:
            return self._heuristic_clean(text)

        try:
            payload = {
                "model":  self._model,
                "stream": False,
                "options": {
                    "temperature": 0.15,
                    "num_predict": 2500,
                },
                "messages": [
                    {
                        "role":    "user",
                        "content": CLEANUP_PROMPT + text,
                    }
                ],
            }
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload, timeout=120,
            )
            r.raise_for_status()
            result = r.json().get("message", {}).get("content", "").strip()
            return result if result else self._heuristic_clean(text)
        except Exception:
            # Network/timeout — fall back to heuristic
            return self._heuristic_clean(text)

    # ── heuristic fallback (no LLM needed) ───────────────────
    @staticmethod
    def _heuristic_clean(text: str) -> str:
        """
        Rule-based fixes applied when no cleanup LLM is available.
        Catches the most common OCR errors on chemistry notes.
        """
        fixes = {
            # chemical formulas
            r'\bH2O\b':   'H₂O',
            r'\bCaCl2\b': 'CaCl₂',
            r'\bCaCl22\b':'CaCl₂',
            r'\bHgO\b':   'HgO',    # keep as-is (genuine compound)
            r'\bAl2O3\b': 'Al₂O₃',
            r'\bFe2O3\b': 'Fe₂O₃',
            r'\bKMnO4\b': 'KMnO₄',
            r'\bH2SO4\b': 'H₂SO₄',
            r'\bH2S\b':   'H₂S',
            r'\bCO2\b':   'CO₂',
            r'\bNH3\b':   'NH₃',
            r'\bSO2\b':   'SO₂',
            r'\bFe3\+':   'Fe³⁺',
            r'\bM\^n\+':  'Mⁿ⁺',

            # common spelling fixes (chemistry notes)
            r'\bAcisorption\b':    'Adsorption',
            r'\badsopption\b':     'adsorption',
            r'\badsoorption\b':    'adsorption',
            r'\bdesorptio\b':      'desorption',
            r'\badsorberen\b':     'adsorbent',
            r'\balosobcile\b':     'adsorbate',
            r'\badsorbat\b':       'adsorbate',
            r'\badsorbcile\b':     'adsorbate',
            r'\bEunctionlich\b':   'Freundlich',
            r'\bFaundlich\b':      'Freundlich',
            r'\bFaeundllich\b':    'Freundlich',
            r'\bLangmuier\b':      'Langmuir',
            r'\bLangmuire\b':      'Langmuir',
            r'\bphysiadsorption\b':'physiosorption',
            r'\bChemisrooion\b':   'Chemisorption',
            r'\bchemisooion\b':    'chemisorption',
            r'\bphysiosorption\b': 'Physiosorption',
            r'\bphysissorption\b': 'Physiosorption',
        }
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Wrap obvious math that slipped through
        text = re.sub(r'\bDelta\s*H\b', r'$\\Delta H$', text)
        text = re.sub(r'\bDelta\s*G\b', r'$\\Delta G$', text)
        text = re.sub(r'\bDelta\s*S\b', r'$\\Delta S$', text)

        return text
