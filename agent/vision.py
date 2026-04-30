"""
agent/vision.py
Multi-engine extraction: vision models (Ollama) + traditional OCR fallbacks.

Engines:
  minicpm-v / llava  — Ollama /api/chat multimodal (best for handwriting)
  easyocr            — deep learning OCR (printed text)
  tesseract          — classical OCR (typed/printed)
  paddleocr          — PaddlePaddle OCR
"""

import base64, io, json, re, time
import requests
from PIL import Image, ImageEnhance

from config import (
    OLLAMA_URL, ENGINES, DEFAULT_ENGINE,
    SYSTEM_PROMPT, PROMPTS,
    MAX_RETRIES, QUALITY_THRESHOLD, STREAM_TOKENS, MAX_IMAGE_DIM,
)


# ── engine availability check (run once at startup) ──────────
def available_engines() -> list[dict]:
    """Return engines with an 'available' flag set."""
    result = []
    for eng in ENGINES:
        e = dict(eng)
        if e["type"] == "vision":
            # Will be checked live against Ollama tags
            e["available"] = True   # optimistic; real check in OllamaVision
        elif e["key"] == "easyocr":
            try:
                import easyocr; e["available"] = True
            except ImportError:
                e["available"] = False
        elif e["key"] == "tesseract":
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                e["available"] = True
            except Exception:
                e["available"] = False
        elif e["key"] == "paddleocr":
            try:
                from paddleocr import PaddleOCR; e["available"] = True
            except ImportError:
                e["available"] = False
        result.append(e)
    return result


class OllamaVision:
    """Handles vision-model extraction via Ollama /api/chat."""

    @staticmethod
    def check_connection(model: str | None = None) -> tuple[bool, str]:
        mdl = model or DEFAULT_ENGINE
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            base   = mdl.split(":")[0]
            found  = any(base in m for m in models)
            if not found:
                avail = ", ".join(models) or "none"
                return False, (
                    f"Model '{mdl}' not found.\n"
                    f"Available: {avail}\n"
                    f"Run:  ollama pull {mdl}"
                )
            return True, f"Ollama  ·  {mdl}"
        except requests.ConnectionError:
            return False, "Cannot reach Ollama on localhost:11434.\nRun:  ollama serve"
        except Exception as e:
            return False, f"Connection error: {e}"

    def extract(self, image_path, model, progress_cb=None, token_cb=None):
        if progress_cb:
            progress_cb("🔍 Perception — preprocessing image")
        img_b64 = self._encode(image_path)

        best_text, best_q = "", {"score": 0.0}
        retries = 0

        for attempt in range(1, MAX_RETRIES + 1):
            if progress_cb:
                progress_cb(f"🧠 Vision extraction — attempt {attempt}/{MAX_RETRIES}")
            text    = self._call(img_b64, model, attempt, token_cb)
            quality = self._score(text)

            if quality["score"] > best_q["score"]:
                best_text, best_q = text, quality

            retries = attempt - 1
            if quality["score"] >= QUALITY_THRESHOLD:
                break
            if attempt < MAX_RETRIES:
                if progress_cb:
                    progress_cb(f"⚠  Quality {quality['score']:.0%} — retrying…")
                time.sleep(1.0)

        return best_text, best_q, retries

    def _call(self, img_b64, model, attempt, token_cb):
        payload = {
            "model":  model,
            "stream": STREAM_TOKENS and token_cb is not None,
            "options": {
                "temperature":    0.1,
                "num_predict":    1600,
                "repeat_penalty": 1.4,
                "repeat_last_n":  128,
                "top_p":          0.85,
            },
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": PROMPTS.get(attempt, PROMPTS[2]),
                 "images": [img_b64]},
            ],
        }
        try:
            if payload["stream"]:
                return self._stream(payload, token_cb)
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
            r.raise_for_status()
            return self._clean(r.json().get("message", {}).get("content", "").strip())
        except requests.Timeout:
            raise RuntimeError("Ollama timed out. Wait 30s and retry.")
        except requests.ConnectionError:
            raise RuntimeError("Lost Ollama connection. Ensure 'ollama serve' is running.")

    def _stream(self, payload, token_cb):
        buf, n = [], 0
        with requests.post(f"{OLLAMA_URL}/api/chat",
                           json=payload, stream=True, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line: continue
                try:
                    data  = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        buf.append(token); token_cb(token); n += 1
                        if self._is_looping("".join(buf[-60:])):
                            token_cb("\n\n[repetition stopped]"); break
                        if n >= 1600:
                            token_cb("\n\n[token cap]"); break
                    if data.get("done"): break
                except json.JSONDecodeError:
                    continue
        return self._clean("".join(buf).strip())

    @staticmethod
    def _encode(path):
        img = Image.open(path).convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIM:
            s = MAX_IMAGE_DIM / max(w, h)
            img = img.resize((int(w*s), int(h*s)), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Sharpness(img).enhance(1.7)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=93)
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def _is_looping(tail):
        if re.search(r'([^\s])\1{5,}', tail): return True
        if re.search(r'(\S+)( \1){4,}',  tail): return True
        if re.search(r'(#{1,4} [^\n]{1,30}\n)\1{2,}', tail): return True
        if tail.count("most common method") >= 2: return True
        return False

    @staticmethod
    def _clean(text):
        # strip code fences
        text = re.sub(r'^```(?:markdown|text)?\n?', '', text, flags=re.M)
        text = re.sub(r'\n?```\s*$', '',              text, flags=re.M)

        lines   = text.splitlines()
        cleaned = []
        seen    = {}   # normalised_line → count

        for line in lines:
            s   = line.strip()
            key = re.sub(r'\s+', ' ', s.lower())

            # Drop pure-repetition char lines (∝∝∝∝)
            if s and len(set(s)) == 1 and len(s) > 3:
                continue

            # Deduplicate: allow short lines twice, long lines once
            limit = 1 if len(key) > 40 else 2
            seen[key] = seen.get(key, 0) + 1
            if key and seen[key] > limit:
                continue

            cleaned.append(line)

        return re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned)).strip()

    @staticmethod
    def _score(text):
        if not text or len(text.strip()) < 30:
            return {"score": 0.05, "word_count": 0, "eq_count": 0}
        words     = len(text.split())
        has_str   = bool(re.search(r'^#{1,4}\s', text, re.M))
        has_bul   = bool(re.search(r'^\s*[-•*]\s', text, re.M))
        has_eqs   = bool(re.search(r'\$[^$]+\$|[αβγδΔ∝⇌→]|[A-Z][a-z]?[₀-₉]', text))
        eq_count  = len(re.findall(r'\$[^$]+\$', text))
        score = min(
            min(words/150, 1.0)*0.30
            + (0.25 if has_str  else 0.05)
            + (0.25 if has_eqs  else 0.05)
            + (0.20 if has_bul  else 0.05),
            1.0)
        return {"score": round(score, 3), "word_count": words, "eq_count": eq_count}


# ── Traditional OCR engines ───────────────────────────────────

class EasyOCREngine:
    _reader = None

    def extract(self, image_path, progress_cb=None, token_cb=None):
        if progress_cb: progress_cb("🧠 EasyOCR — loading model…")
        try:
            import easyocr
            if EasyOCREngine._reader is None:
                EasyOCREngine._reader = easyocr.Reader(['en'], gpu=True)
            results = EasyOCREngine._reader.readtext(image_path, detail=0)
            text    = "\n".join(results)
            if token_cb: token_cb(text)
            q = OllamaVision._score(text)
            return text, q, 0
        except ImportError:
            raise RuntimeError(
                "EasyOCR not installed.\n"
                "Run:  pip install easyocr"
            )


class TesseractEngine:
    def extract(self, image_path, progress_cb=None, token_cb=None):
        if progress_cb: progress_cb("🧠 Tesseract — extracting…")
        try:
            import pytesseract
            from PIL import Image as PImg
            img  = PImg.open(image_path)
            text = pytesseract.image_to_string(img, lang="eng")
            if token_cb: token_cb(text)
            q = OllamaVision._score(text)
            return text, q, 0
        except ImportError:
            raise RuntimeError("pytesseract not installed.\nRun:  pip install pytesseract")
        except Exception as e:
            raise RuntimeError(
                f"Tesseract error: {e}\n"
                "Ensure Tesseract is installed: https://github.com/UB-Mannheim/tesseract/wiki"
            )


class PaddleOCREngine:
    _ocr = None

    def extract(self, image_path, progress_cb=None, token_cb=None):
        if progress_cb: progress_cb("🧠 PaddleOCR — extracting…")
        try:
            from paddleocr import PaddleOCR
            if PaddleOCREngine._ocr is None:
                PaddleOCREngine._ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)
            result = PaddleOCREngine._ocr.ocr(image_path, cls=True)
            lines  = []
            for block in (result or []):
                for line in (block or []):
                    if line and len(line) >= 2:
                        txt = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                        lines.append(txt)
            text = "\n".join(lines)
            if token_cb: token_cb(text)
            q = OllamaVision._score(text)
            return text, q, 0
        except ImportError:
            raise RuntimeError(
                "PaddleOCR not installed.\n"
                "Run:  pip install paddlepaddle==2.6.2 paddleocr==2.7.3"
            )


def get_engine(engine_key: str):
    """Factory — returns the correct engine instance for a key."""
    if engine_key in ("minicpm-v", "llava"):
        return OllamaVision(), "vision"
    if engine_key == "easyocr":
        return EasyOCREngine(), "ocr"
    if engine_key == "tesseract":
        return TesseractEngine(), "ocr"
    if engine_key == "paddleocr":
        return PaddleOCREngine(), "ocr"
    return OllamaVision(), "vision"   # default
