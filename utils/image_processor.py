"""
utils/image_processor.py
OpenCV image preprocessing pipeline.

Three levels controlled by PREPROCESS_LEVEL in config.py:
  "light"  — resize only (fastest; good for already clear images)
  "medium" — denoise + CLAHE contrast boost (recommended)
  "heavy"  — adaptive threshold (slowest; crumpled / faded pages)
"""

import cv2
import numpy as np
from PIL import Image
from config import PREPROCESS_LEVEL, MAX_IMAGE_DIM


def preprocess(image_path: str) -> np.ndarray:
    """
    Load image from path, apply preprocessing, return BGR ndarray.
    The vision module calls this before base64 encoding.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot open image: {image_path}")

    img = _fix_rotation(image_path, img)
    img = _resize(img, MAX_IMAGE_DIM)

    if PREPROCESS_LEVEL == "medium":
        img = _medium(img)
    elif PREPROCESS_LEVEL == "heavy":
        img = _heavy(img)
    # "light" → just resize (done above)

    return img


def thumbnail_pil(image_path: str, max_w: int = 340, max_h: int = 280) -> Image.Image:
    """Return a PIL thumbnail for display in the UI."""
    img = Image.open(image_path)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


# ── preprocessing levels ─────────────────────────────────────

def _resize(img: np.ndarray, max_dim: int) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return img
    scale = max_dim / max(h, w)
    return cv2.resize(img, (int(w*scale), int(h*scale)),
                      interpolation=cv2.INTER_LANCZOS4)

def _medium(img: np.ndarray) -> np.ndarray:
    """Denoise + CLAHE contrast on L channel → sharpening."""
    # Fast denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 8, 8, 7, 21)

    # CLAHE on L channel (avoids colour shift)
    lab    = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe  = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l      = clahe.apply(l)
    img    = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

    # Mild unsharp mask
    kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
    return cv2.filter2D(img, -1, kernel)

def _heavy(img: np.ndarray) -> np.ndarray:
    """Grayscale → strong denoise → adaptive threshold.
    Makes text very crisp but loses colour (fine for B&W notes)."""
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray  = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=25, C=8,
    )
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

def _fix_rotation(path: str, img: np.ndarray) -> np.ndarray:
    """Correct EXIF rotation (common in phone photos)."""
    try:
        from PIL import Image as PImg
        from PIL.ExifTags import TAGS
        pil  = PImg.open(path)
        exif = pil._getexif()
        if not exif:
            return img
        for tag, val in exif.items():
            if TAGS.get(tag) == "Orientation":
                if   val == 3: img = cv2.rotate(img, cv2.ROTATE_180)
                elif val == 6: img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif val == 8: img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                break
    except Exception:
        pass
    return img
