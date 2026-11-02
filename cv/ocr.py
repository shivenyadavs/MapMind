"""Optional lightweight OCR helpers for semantic floor-plan labels.

Tesseract is not a mandatory dependency. When ``pytesseract`` and the
Tesseract executable are available, labels are extracted and associated with
segmented regions. Otherwise the pipeline keeps generic Room/Corridor names
and reports that OCR was unavailable.

No models are downloaded and no heavy OCR dependency is imported at module
load time.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class OCRToken:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    line_key: str = ""


_LABEL_ALIASES: Dict[str, str] = {
    "store": "Store",
    "shop": "Store",
    "retail": "Store",
    "restaurant": "Restaurant",
    "resturant": "Restaurant",
    "cafe": "Cafe",
    "café": "Cafe",
    "coffee": "Cafe",
    "hall": "Hall",
    "corridor": "Corridor",
    "passage": "Corridor",
    "rest area": "Rest Area",
    "restroom": "Toilet",
    "toilet": "Toilet",
    "washroom": "Toilet",
    "wc": "Toilet",
    "stairs": "Stairwell",
    "stair": "Stairwell",
    "stairwell": "Stairwell",
    "elevator": "Elevator",
    "lift": "Elevator",
    "office": "Mall Office",
    "mall office": "Mall Office",
    "management office": "Mall Office",
}

_NON_LABEL_RE = re.compile(
    r"^(?:[\d.,:/\\\-\s]+|(?:mm|cm|m|ft|in|px)\b|[A-Za-z]\d{0,2})$",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = value.strip(".,:;|_/\\-–—")
    return value


def normalize_label(text: str) -> Tuple[Optional[str], float]:
    """Return a conservative canonical label and classification confidence.

    Unknown but legible text is *not* forced into a semantic category. The
    caller may still use it as a printed room/shop name with classification
    confidence 0.
    """
    value = normalize_text(text)
    if not value:
        return None, 0.0
    key = re.sub(r"[^a-z0-9 ]", "", value.casefold()).strip()
    key = re.sub(r"\s+", " ", key)
    if key in _LABEL_ALIASES:
        return _LABEL_ALIASES[key], 0.8
    return None, 0.0


def is_plausible_label(text: str, confidence: float, min_confidence: float = 35.0) -> bool:
    value = normalize_text(text)
    if confidence < min_confidence or len(value) < 2:
        return False
    if not any(ch.isalpha() for ch in value):
        return False
    if _NON_LABEL_RE.match(value):
        return False
    return True


def _load_pytesseract() -> Optional[Any]:
    try:
        import pytesseract  # type: ignore

        return pytesseract
    except Exception:
        return None


def extract_text_tokens(
    image_bgr: np.ndarray,
    min_confidence: float = 35.0,
    backend: Optional[Callable[[np.ndarray], Dict[str, List[Any]]]] = None,
) -> Tuple[List[OCRToken], Dict[str, Any]]:
    """Extract OCR tokens from a BGR image.

    Parameters
    ----------
    image_bgr:
        Source image. OCR is run on grayscale at the supplied resolution.
    min_confidence:
        Reject low-confidence OCR tokens.
    backend:
        Optional callable returning a pytesseract-like ``image_to_data`` dict.
        It exists so tests can exercise token parsing without Tesseract.
    """
    diagnostics: Dict[str, Any] = {"available": False, "backend": "unavailable", "error": None}
    data: Optional[Dict[str, List[Any]]] = None

    if backend is not None:
        try:
            data = backend(image_bgr)
            diagnostics["available"] = True
            diagnostics["backend"] = "injected"
        except Exception as exc:
            diagnostics["error"] = str(exc)
            return [], diagnostics
    else:
        pytesseract = _load_pytesseract()
        if pytesseract is None:
            diagnostics["error"] = "pytesseract is not installed"
            return [], diagnostics
        if shutil.which("tesseract") is None:
            diagnostics["error"] = "Tesseract executable not found on PATH"
            return [], diagnostics
        try:
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            data = pytesseract.image_to_data(
                gray,
                output_type=pytesseract.Output.DICT,
                config="--psm 11",
            )
            diagnostics["available"] = True
            diagnostics["backend"] = "pytesseract"
        except Exception as exc:
            diagnostics["error"] = str(exc)
            return [], diagnostics

    if not data:
        return [], diagnostics

    texts = data.get("text", [])
    tokens: List[OCRToken] = []
    for idx, raw_text in enumerate(texts):
        text = normalize_text(raw_text)
        if not text:
            continue
        try:
            confidence = float(data.get("conf", [0] * len(texts))[idx])
        except (TypeError, ValueError, IndexError):
            confidence = 0.0
        if not is_plausible_label(text, confidence, min_confidence=min_confidence):
            continue
        try:
            x = int(data.get("left", [0] * len(texts))[idx])
            y = int(data.get("top", [0] * len(texts))[idx])
            w = int(data.get("width", [0] * len(texts))[idx])
            h = int(data.get("height", [0] * len(texts))[idx])
        except (TypeError, ValueError, IndexError):
            continue
        if w <= 0 or h <= 0:
            continue
        line_key = "{}:{}:{}".format(
            data.get("block_num", [0] * len(texts))[idx],
            data.get("par_num", [0] * len(texts))[idx],
            data.get("line_num", [0] * len(texts))[idx],
        )
        tokens.append(OCRToken(text=text, confidence=confidence, bbox=(x, y, w, h), line_key=line_key))

    diagnostics["token_count"] = len(tokens)
    return tokens, diagnostics
