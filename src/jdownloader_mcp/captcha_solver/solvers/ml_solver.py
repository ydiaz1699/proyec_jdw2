"""
ML Solver - Deep Learning captcha solver using custom CNN.
===========================================================
Uses a self-trained CNN model for recognizing captcha characters.
Does NOT depend on any external service — runs completely offline.

The model can be trained on captcha samples collected from specific hosters.

Usage:
    solver = MLSolver(config={
        "model_path": "./models/k2s_model.pth",
        "charset": "0123456789ABCDEF",
        "expected_length": 6,
    })
    solution = solver.solve(challenge)

Training new models:
    solver = MLSolver()
    stats = solver.train(
        data_dir="./data/k2s_chars/",
        save_path="./models/k2s_model.pth",
        epochs=20,
    )
"""

import os
import logging
from typing import Optional

from ..base import BaseSolver, CaptchaChallenge, CaptchaSolution, CaptchaType
from ..preprocessing import ImageProcessor

logger = logging.getLogger("captcha-solver.ml")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class MLSolver(BaseSolver):
    """
    Solves text/image captchas using a custom-trained CNN model.

    Config options:
        model_path: Path to trained .pth model file
        charset: Character set the model was trained on
        expected_length: Expected captcha length (0 = auto from segmentation)
        img_size: Model input size (default: 32)
        confidence_threshold: Minimum confidence to accept (default: 0.5)
        preprocessing: "auto", "default", "hoster"
    """

    name = "ml_cnn"
    supported_types = [CaptchaType.TEXT_IMAGE, CaptchaType.GEOMETRIC]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)

        self.model_path = self.config.get("model_path", "")
        self.charset = self.config.get("charset", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.expected_length = self.config.get("expected_length", 0)
        self.img_size = self.config.get("img_size", 32)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        self.preprocessing_mode = self.config.get("preprocessing", "auto")

        self._model = None

        if not HAS_TORCH:
            logger.warning("PyTorch not available. ML solver disabled.")
            self.enabled = False
            return

        # Try to load model
        if self.model_path and os.path.exists(self.model_path):
            self._load_model()
        else:
            logger.info(
                f"ML Solver: No model at '{self.model_path}'. "
                f"Train one with solver.train() or provide a valid path."
            )
            self.enabled = False

    def _load_model(self):
        """Load the CNN model."""
        try:
            from ..models.cnn_model import CaptchaCNN

            self._model = CaptchaCNN(
                num_classes=len(self.charset),
                img_size=self.img_size,
                charset=self.charset,
                model_path=self.model_path,
            )
            self.enabled = True
            logger.info(f"ML model loaded: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            self.enabled = False

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a captcha using the trained CNN model."""
        if self._model is None:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="No model loaded. Train one first.",
            )

        # Get image
        img = self._get_image(challenge)
        if img is None:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="Failed to load captcha image",
            )

        try:
            # Predict full captcha
            text, confidence = self._model.predict_captcha(
                img, num_chars=self.expected_length
            )

            # Check confidence threshold
            if confidence < self.confidence_threshold:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    confidence=confidence,
                    error=f"Low confidence: {confidence:.2%} < {self.confidence_threshold:.2%}",
                )

            if not text:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="Model returned empty prediction",
                )

            return CaptchaSolution(
                success=True,
                solution=text,
                solver_name=self.name,
                confidence=confidence,
            )

        except Exception as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"Prediction error: {e}",
            )

    def train(
        self,
        data_dir: str,
        save_path: Optional[str] = None,
        epochs: int = 20,
        batch_size: int = 64,
        learning_rate: float = 0.001,
    ) -> dict:
        """
        Train a new model on captcha character data.

        Args:
            data_dir: Directory with character images organized as:
                      data_dir/0/img1.png, data_dir/A/img2.png, etc.
            save_path: Where to save the trained model (default: self.model_path)
            epochs: Training epochs
            batch_size: Batch size
            learning_rate: Learning rate

        Returns:
            Training statistics dict
        """
        if not HAS_TORCH:
            return {"error": "PyTorch not installed. Run: pip install torch torchvision"}

        from ..models.cnn_model import CaptchaCNN

        save_path = save_path or self.model_path or "./models/captcha_cnn.pth"

        # Create and train model
        model = CaptchaCNN(
            num_classes=len(self.charset),
            img_size=self.img_size,
            charset=self.charset,
        )

        stats = model.train_on_dataset(
            data_dir=data_dir,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            save_path=save_path,
        )

        if "error" not in stats:
            # Reload the trained model
            self.model_path = save_path
            self._model = model
            self.enabled = True
            logger.info(f"Training complete. Model saved to: {save_path}")

        return stats

    def _get_image(self, challenge: CaptchaChallenge):
        """Extract PIL Image from challenge."""
        if challenge.image_data:
            return ImageProcessor.from_bytes(challenge.image_data)
        elif challenge.image_base64:
            return ImageProcessor.from_base64(challenge.image_base64)
        return None

    @staticmethod
    def generate_training_data(
        captcha_images_dir: str,
        output_dir: str,
        labels_file: Optional[str] = None,
    ) -> dict:
        """
        Helper to prepare training data from full captcha images.

        Takes a folder of captcha images with known labels and segments
        them into individual character images organized by class.

        Args:
            captcha_images_dir: Folder with captcha images
            output_dir: Output folder for segmented characters
            labels_file: Optional file mapping filename → label text
                         (one per line: "img001.png,ABC123")
                         If None, filename prefix is used as label.

        Returns:
            Stats about generated data
        """
        if not HAS_PIL:
            return {"error": "Pillow not installed"}

        from PIL import Image as PILImage

        os.makedirs(output_dir, exist_ok=True)
        stats = {"total_images": 0, "total_chars": 0, "errors": 0}

        # Load labels
        labels = {}
        if labels_file and os.path.exists(labels_file):
            with open(labels_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if "," in line:
                        fname, label = line.split(",", 1)
                        labels[fname.strip()] = label.strip()

        # Process each image
        for fname in sorted(os.listdir(captcha_images_dir)):
            if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                continue

            # Determine label
            if fname in labels:
                label = labels[fname]
            else:
                # Use filename prefix (before first dot or underscore)
                label = fname.split(".")[0].split("_")[0]

            if not label:
                continue

            try:
                img_path = os.path.join(captcha_images_dir, fname)
                img = PILImage.open(img_path)

                # Preprocess and segment
                processed = ImageProcessor.full_pipeline(img, scale_factor=1.0)
                chars = ImageProcessor.segment_characters(processed, len(label))

                if len(chars) != len(label):
                    stats["errors"] += 1
                    continue

                # Save each character
                for i, (char_img, char_label) in enumerate(zip(chars, label)):
                    char_dir = os.path.join(output_dir, char_label.upper())
                    os.makedirs(char_dir, exist_ok=True)

                    char_path = os.path.join(
                        char_dir,
                        f"{fname.split('.')[0]}_{i}.png"
                    )
                    char_img.save(char_path)
                    stats["total_chars"] += 1

                stats["total_images"] += 1

            except Exception as e:
                logger.debug(f"Error processing {fname}: {e}")
                stats["errors"] += 1

        return stats
