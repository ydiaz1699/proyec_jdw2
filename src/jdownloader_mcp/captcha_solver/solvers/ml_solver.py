"""
ML Solver
=========
Solves text/image captchas using a custom-trained CNN model.
Uses PyTorch for inference with a pre-trained captcha recognition model.

Requires:
- torch >= 2.0.0
- torchvision >= 0.15.0
- numpy >= 1.24.0

NOTE: este solver es opt-in. No se registra por defecto (ver README) y necesita,
además de torch, un modelo CNN entrenado (.pth) que este repo no incluye. Los
anotaciones de tipo se difieren con ``from __future__ import annotations`` para
que el módulo pueda importarse sin torch sin lanzar NameError.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Optional

from ..base import (
    BaseSolver,
    CaptchaChallenge,
    CaptchaSolution,
    CaptchaType,
)

logger = logging.getLogger("captcha-solver.ml")


# Try to import ML dependencies
_torch_available = False

try:
    import torch
    import numpy as np
    _torch_available = True
except ImportError:
    pass

# Character set for captcha decoding
DEFAULT_CHARSET = "0123456789abcdefghijklmnopqrstuvwxyz"
DEFAULT_CAPTCHA_LENGTH = 6
DEFAULT_IMAGE_WIDTH = 160
DEFAULT_IMAGE_HEIGHT = 60


class MLSolver(BaseSolver):
    """
    Solver that uses a custom-trained CNN model to recognize
    text captchas. Faster and more accurate than OCR for known
    captcha types when properly trained.
    """

    name = "ml"
    supported_types = [CaptchaType.TEXT_IMAGE]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.model_path = self.config.get("model_path", "")
        self.charset = self.config.get("charset", DEFAULT_CHARSET)
        self.captcha_length = self.config.get(
            "captcha_length", DEFAULT_CAPTCHA_LENGTH
        )
        self.image_width = self.config.get("image_width", DEFAULT_IMAGE_WIDTH)
        self.image_height = self.config.get(
            "image_height", DEFAULT_IMAGE_HEIGHT
        )
        self.confidence_threshold = self.config.get(
            "confidence_threshold", 0.5
        )

        self._model = None
        self._device = None

        if not _torch_available:
            logger.warning("PyTorch not available - ML solver disabled")
            self.enabled = False
        elif self.model_path and not os.path.exists(self.model_path):
            logger.warning(
                f"Model file not found: {self.model_path} - "
                "ML solver disabled"
            )
            self.enabled = False


    def _load_model(self):
        """Lazy-load the ML model."""
        if self._model is not None:
            return

        from ..models.cnn_model import CaptchaCNN

        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        num_classes = len(self.charset)
        self._model = CaptchaCNN(
            num_classes=num_classes,
            captcha_length=self.captcha_length,
            image_height=self.image_height,
            image_width=self.image_width,
        )

        if self.model_path and os.path.exists(self.model_path):
            state_dict = torch.load(
                self.model_path,
                map_location=self._device,
                weights_only=True,
            )
            self._model.load_state_dict(state_dict)
            logger.info(f"Loaded model from {self.model_path}")

        self._model.to(self._device)
        self._model.eval()

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a text/image captcha using the trained CNN."""
        try:
            self._load_model()

            image = self._load_image(challenge)
            if image is None:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="Failed to load captcha image",
                )

            tensor = self._preprocess(image)
            text, confidence = self._predict(tensor)

            if confidence >= self.confidence_threshold:
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
                    error=(
                        f"Low confidence: {confidence:.2f} "
                        f"(threshold: {self.confidence_threshold})"
                    ),
                )

        except Exception as e:
            logger.error(f"ML solver error: {e}")
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
        """Preprocess image for the CNN model."""
        from torchvision import transforms

        transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((self.image_height, self.image_width)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ])

        tensor = transform(image)
        # Add batch dimension
        tensor = tensor.unsqueeze(0).to(self._device)
        return tensor

    def _predict(self, tensor) -> tuple:
        """Run prediction and return (text, confidence)."""
        # torch.no_grad() se usa como context manager DENTRO del método, no como
        # decorador a nivel de clase: un decorador se evalúa al definir la clase
        # y lanzaría NameError si torch no está instalado al importar el módulo.
        with torch.no_grad():
            outputs = self._model(tensor)
            # outputs shape: (batch, captcha_length, num_classes)

            probabilities = torch.softmax(outputs, dim=2)
            max_probs, predictions = torch.max(probabilities, dim=2)

            # Decode predictions to text
            pred_indices = predictions[0].cpu().numpy()
            char_probs = max_probs[0].cpu().numpy()

        text = ""
        for idx in pred_indices:
            if idx < len(self.charset):
                text += self.charset[idx]

        # Average confidence across all characters
        confidence = float(np.mean(char_probs))

        return text, confidence
