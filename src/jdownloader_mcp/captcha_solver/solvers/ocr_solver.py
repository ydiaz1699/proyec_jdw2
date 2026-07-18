"""
OCR Solver - Text captcha solver using Tesseract and/or EasyOCR.
==================================================================
Self-contained OCR solver that doesn't depend on external captcha services.
Uses local OCR engines to read text from captcha images.

Supported engines:
- Tesseract OCR (via pytesseract)
- EasyOCR (PyTorch-based, better for distorted text)
- Both (ensemble: tries both and picks the best result)

Install:
    pip install pytesseract Pillow
    # Also install tesseract-ocr system package:
    # Ubuntu: sudo apt install tesseract-ocr
    # Mac: brew install tesseract
    # Windows: download from https://github.com/UB-Mannheim/tesseract

    # Optional (better accuracy on distorted text):
    pip install easyocr
"""

import io
import re
import logging
from typing import Optional

from ..base import BaseSolver, CaptchaChallenge, CaptchaSolution, CaptchaType
from ..preprocessing import ImageProcessor

logger = logging.getLogger("captcha-solver.ocr")

# Check available OCR engines
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import easyocr
    HAS_EASYOCR = True
    _easyocr_reader = None  # Lazy init
except ImportError:
    HAS_EASYOCR = False


def _get_easyocr_reader():
    """Lazy-initialize EasyOCR reader (heavy on first load)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(
            ["en"],
            gpu=False,  # CPU by default, set True if GPU available
            verbose=False,
        )
    return _easyocr_reader


class OCRSolver(BaseSolver):
    """
    Solves text/image captchas using local OCR engines.

    Config options:
        engine: "tesseract", "easyocr", "both" (default: auto-detect)
        char_whitelist: Allowed characters (e.g., "0123456789ABCDEF")
        expected_length: Expected number of characters (0 = any)
        tesseract_config: Extra tesseract config string
        preprocessing: "auto", "default", "hoster" (default: "auto")
    """

    name = "ocr_local"
    supported_types = [CaptchaType.TEXT_IMAGE]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)

        # Determine which engine to use
        self.engine = self.config.get("engine", "auto")
        if self.engine == "auto":
            if HAS_EASYOCR:
                self.engine = "both"
            elif HAS_TESSERACT:
                self.engine = "tesseract"
            else:
                self.engine = "none"
                logger.warning(
                    "No OCR engine available. Install pytesseract or easyocr."
                )

        self.char_whitelist = self.config.get("char_whitelist", "")
        self.expected_length = self.config.get("expected_length", 0)
        self.tesseract_config = self.config.get("tesseract_config", "")
        self.preprocessing_mode = self.config.get("preprocessing", "auto")

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a text/image captcha using OCR."""
        if self.engine == "none":
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="No OCR engine installed",
            )

        # Get image
        img = self._get_image(challenge)
        if img is None:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="Failed to load captcha image",
            )

        # Preprocess
        processed = self._preprocess(img, challenge.hoster)

        # Run OCR
        results = []

        if self.engine in ("tesseract", "both") and HAS_TESSERACT:
            text = self._ocr_tesseract(processed)
            if text:
                results.append(("tesseract", text))

        if self.engine in ("easyocr", "both") and HAS_EASYOCR:
            text = self._ocr_easyocr(processed)
            if text:
                results.append(("easyocr", text))

        if not results:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="OCR returned no text",
            )

        # Pick best result
        best_text, confidence = self._pick_best(results)

        if best_text:
            return CaptchaSolution(
                success=True,
                solution=best_text,
                solver_name=self.name,
                confidence=confidence,
            )

        return CaptchaSolution(
            success=False,
            solver_name=self.name,
            error="OCR result didn't match expected format",
        )

    def _get_image(self, challenge: CaptchaChallenge):
        """Extract PIL Image from challenge."""
        if challenge.image_data:
            return ImageProcessor.from_bytes(challenge.image_data)
        elif challenge.image_base64:
            return ImageProcessor.from_base64(challenge.image_base64)
        return None

    def _preprocess(self, img, hoster: str):
        """Apply preprocessing pipeline."""
        if self.preprocessing_mode == "hoster" and hoster:
            return ImageProcessor.pipeline_for_hoster(img, hoster)
        else:
            return ImageProcessor.full_pipeline(img)

    def _ocr_tesseract(self, img) -> str:
        """Run Tesseract OCR on preprocessed image."""
        try:
            config = "--psm 7"  # Single text line
            if self.char_whitelist:
                config += f" -c tessedit_char_whitelist={self.char_whitelist}"
            if self.tesseract_config:
                config += f" {self.tesseract_config}"

            text = pytesseract.image_to_string(img, config=config)
            return self._clean_text(text)
        except Exception as e:
            logger.debug(f"Tesseract error: {e}")
            return ""

    def _ocr_easyocr(self, img) -> str:
        """Run EasyOCR on preprocessed image."""
        try:
            reader = _get_easyocr_reader()

            # Convert PIL to bytes for easyocr
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            results = reader.readtext(
                img_bytes,
                detail=1,
                paragraph=False,
                allowlist=self.char_whitelist or None,
            )

            if results:
                # Concatenate all detected text
                text = "".join([r[1] for r in results])
                return self._clean_text(text)
            return ""
        except Exception as e:
            logger.debug(f"EasyOCR error: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Clean OCR output: remove whitespace, fix common misreads."""
        if not text:
            return ""

        # Remove whitespace and newlines
        text = text.strip().replace(" ", "").replace("\n", "")

        # Common OCR substitutions
        replacements = {
            "O": "0",  # Letter O → zero (context-dependent)
            "l": "1",  # lowercase L → one
            "I": "1",  # uppercase I → one
            "S": "5",  # S → 5
            "B": "8",  # B → 8
        }

        # Only apply if whitelist is digits-only
        if self.char_whitelist and self.char_whitelist.isdigit():
            for old, new in replacements.items():
                text = text.replace(old, new)

        # Remove non-whitelist characters if whitelist is set
        if self.char_whitelist:
            text = "".join(c for c in text if c in self.char_whitelist)

        # If we expect a specific length, try to match
        if self.expected_length > 0 and len(text) != self.expected_length:
            # Try removing extra characters from edges
            if len(text) > self.expected_length:
                text = text[:self.expected_length]

        return text

    def _pick_best(self, results: list) -> tuple:
        """
        Pick the best result from multiple OCR engines.
        Returns (text, confidence).
        """
        if not results:
            return "", 0.0

        if len(results) == 1:
            engine, text = results[0]
            confidence = self._estimate_confidence(text)
            return text, confidence

        # Multiple results: prefer the one that matches expected format
        scored = []
        for engine, text in results:
            score = self._estimate_confidence(text)
            scored.append((score, text, engine))

        scored.sort(reverse=True)
        best_score, best_text, best_engine = scored[0]

        # If both agree, high confidence
        if len(scored) >= 2 and scored[0][1] == scored[1][1]:
            return best_text, min(0.95, best_score + 0.2)

        return best_text, best_score

    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence based on text properties."""
        if not text:
            return 0.0

        score = 0.5  # Base score

        # Length matches expected
        if self.expected_length > 0:
            if len(text) == self.expected_length:
                score += 0.3
            else:
                score -= 0.2

        # All characters are in whitelist
        if self.char_whitelist:
            valid_chars = sum(1 for c in text if c in self.char_whitelist)
            if len(text) > 0:
                score += 0.2 * (valid_chars / len(text))

        # Reasonable length (4-8 characters)
        if 4 <= len(text) <= 8:
            score += 0.1

        return min(1.0, max(0.0, score))
