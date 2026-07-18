"""
OCR Solver
==========
Solves text/image captchas using OCR engines (Tesseract and EasyOCR).
Best for simple text captchas with minimal distortion.

Requires:
- pytesseract (+ tesseract-ocr system package)
- OR easyocr (PyTorch-based, better for distorted text)
"""

import base64
import io
import logging
from typing import Optional

from ..base import (
    BaseSolver,
    CaptchaChallenge,
    CaptchaSolution,
    CaptchaType,
)

logger = logging.getLogger("captcha-solver.ocr")

# Try to import OCR engines
_tesseract_available = False
_easyocr_available = False

try:
    import pytesseract
    _tesseract_available = True
except ImportError:
    pass

try:
    import easyocr
    _easyocr_available = True
except ImportError:
    pass


class OCRSolver(BaseSolver):
    """
    Solver that uses OCR engines to read text from captcha images.
    Supports Tesseract and EasyOCR backends.
    """

    name = "ocr"
    supported_types = [CaptchaType.TEXT_IMAGE]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.engine = self.config.get("engine", "auto")
        self.languages = self.config.get("languages", ["en"])
        self.char_whitelist = self.config.get("char_whitelist", "")
        self.psm = self.config.get("psm", 7)  # Single text line

        self._easyocr_reader = None

        if self.engine == "auto":
            if _easyocr_available:
                self.engine = "easyocr"
            elif _tesseract_available:
                self.engine = "tesseract"
            else:
                logger.warning(
                    "No OCR engine available. "
                    "Install pytesseract or easyocr."
                )
                self.enabled = False

        elif self.engine == "tesseract" and not _tesseract_available:
            logger.warning("Tesseract not available")
            self.enabled = False
        elif self.engine == "easyocr" and not _easyocr_available:
            logger.warning("EasyOCR not available")
            self.enabled = False

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a text/image captcha using OCR."""
        try:
            image = self._load_image(challenge)
            if image is None:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="Failed to load captcha image",
                )

            # Apply preprocessing
            image = self._preprocess(image)

            # Run OCR
            if self.engine == "easyocr":
                text = self._ocr_easyocr(image)
            else:
                text = self._ocr_tesseract(image)

            # Clean up the result
            text = self._clean_text(text)

            if text:
                confidence = self._estimate_confidence(text)
                return CaptchaSolution(
                    success=True,
                    solution=text,
                    solver_name=self.name,
                    confidence=confidence,
                )
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="OCR returned empty result",
                )

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=str(e),
            )

    def _load_image(self, challenge: CaptchaChallenge):
        """Load image from challenge data."""
        from PIL import Image

        if challenge.image_data:
            return Image.open(io.BytesIO(challenge.image_data))
        elif challenge.image_base64:
            image_data = base64.b64decode(challenge.image_base64)
            return Image.open(io.BytesIO(image_data))
        return None

    def _preprocess(self, image):
        """Apply basic preprocessing to improve OCR accuracy."""
        from PIL import Image, ImageFilter

        # Convert to grayscale
        if image.mode != "L":
            image = image.convert("L")

        # Resize if too small
        w, h = image.size
        if w < 200 or h < 50:
            scale = max(200 / w, 50 / h, 2.0)
            image = image.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS,
            )

        # Apply slight sharpening
        image = image.filter(ImageFilter.SHARPEN)

        # Threshold to binary
        threshold = self.config.get("threshold", 128)
        image = image.point(lambda p: 255 if p > threshold else 0)

        return image

    def _ocr_tesseract(self, image) -> str:
        """Run Tesseract OCR on the image."""
        custom_config = f"--psm {self.psm}"
        if self.char_whitelist:
            custom_config += f" -c tessedit_char_whitelist={self.char_whitelist}"

        text = pytesseract.image_to_string(
            image,
            lang="+".join(self.languages),
            config=custom_config,
        )
        return text.strip()

    def _ocr_easyocr(self, image) -> str:
        """Run EasyOCR on the image."""
        import numpy as np

        if self._easyocr_reader is None:
            self._easyocr_reader = easyocr.Reader(
                self.languages,
                gpu=False,
            )

        # Convert PIL image to numpy array
        img_array = np.array(image)

        results = self._easyocr_reader.readtext(
            img_array,
            detail=0,
            paragraph=True,
        )

        return " ".join(results).strip() if results else ""

    def _clean_text(self, text: str) -> str:
        """Clean OCR output."""
        # Remove common OCR artifacts
        text = text.strip()
        text = text.replace("\n", "").replace("\r", "")
        text = text.replace(" ", "")

        # If whitelist is set, filter to only allowed characters
        if self.char_whitelist:
            text = "".join(c for c in text if c in self.char_whitelist)

        return text

    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence based on text characteristics."""
        if not text:
            return 0.0

        # Longer text from captchas is usually 4-8 characters
        length = len(text)
        if 4 <= length <= 8:
            confidence = 0.7
        elif 2 <= length <= 10:
            confidence = 0.5
        else:
            confidence = 0.3

        # All alphanumeric is better
        if text.isalnum():
            confidence += 0.1

        return min(confidence, 1.0)
