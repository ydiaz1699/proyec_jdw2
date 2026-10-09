"""
DarkNet/YOLO Solver
===================
Solves geometric/click-based captchas using YOLO object detection.
Based on cracker0dks/CaptchaSolver approach for detecting clickable
objects in visual captchas.

Supports:
- Geometric captchas (click on specific shapes)
- Object selection captchas
- Grid-based image captchas

Requires:
- torch >= 2.0.0
- torchvision >= 0.15.0
- numpy >= 1.24.0

NOTE: este solver es opt-in y no se registra por defecto (ver README). Necesita
torch y un modelo YOLO (.pt) propio. ``from __future__ import annotations``
difiere las anotaciones (p.ej. ``-> torch.Tensor``) para que el módulo se pueda
importar sin torch sin lanzar NameError.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import List, Optional, Tuple

from ..base import (
    BaseSolver,
    CaptchaChallenge,
    CaptchaSolution,
    CaptchaType,
)

logger = logging.getLogger("captcha-solver.darknet")


# Try to import ML dependencies
_torch_available = False

try:
    import torch
    import numpy as np
    _torch_available = True
except ImportError:
    pass


class DarkNetSolver(BaseSolver):
    """
    Solver that uses YOLO/DarkNet-style object detection to solve
    geometric and click-based captchas.

    Detects objects in captcha images and returns coordinates or
    selections based on the detected objects.
    """

    name = "darknet"
    supported_types = [CaptchaType.GEOMETRIC]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.model_path = self.config.get("model_path", "")
        self.confidence_threshold = self.config.get(
            "confidence_threshold", 0.5
        )
        self.nms_threshold = self.config.get("nms_threshold", 0.4)
        self.input_size = self.config.get("input_size", 416)
        self.classes_file = self.config.get("classes_file", "")

        self._model = None
        self._device = None
        self._classes: List[str] = []

        if not _torch_available:
            logger.warning("PyTorch not available - DarkNet solver disabled")
            self.enabled = False
        elif self.model_path and not os.path.exists(self.model_path):
            logger.warning(
                f"YOLO model not found: {self.model_path} - "
                "DarkNet solver disabled"
            )
            self.enabled = False


    def _load_model(self):
        """Lazy-load the YOLO model."""
        if self._model is not None:
            return

        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        # Load class names
        if self.classes_file and os.path.exists(self.classes_file):
            with open(self.classes_file, "r") as f:
                self._classes = [
                    line.strip() for line in f.readlines() if line.strip()
                ]
        else:
            self._classes = ["object"]

        # Load YOLOv5/v8 style model.
        # weights_only=True evita la ejecución de código arbitrario al cargar un
        # .pt no confiable (con weights_only=False torch.load puede ejecutar
        # pickle arbitrario). Si tu modelo requiere objetos personalizados y
        # CONFÍAS en su origen, pon allow_untrusted_model=True en la config.
        if self.model_path and os.path.exists(self.model_path):
            weights_only = not bool(self.config.get("allow_untrusted_model", False))
            self._model = torch.load(
                self.model_path,
                map_location=self._device,
                weights_only=weights_only,
            )
            if isinstance(self._model, dict):
                self._model = self._model.get("model", self._model)

            if hasattr(self._model, "eval"):
                self._model.eval()

            logger.info(
                f"Loaded YOLO model from {self.model_path} "
                f"({len(self._classes)} classes)"
            )

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a geometric/click captcha using object detection."""
        try:
            self._load_model()

            image = self._load_image(challenge)
            if image is None:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="Failed to load captcha image",
                )

            detections = self._detect(image)

            if not detections:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="No objects detected in captcha",
                )

            # Format the solution as coordinates
            solution = self._format_solution(detections, challenge)

            confidence = float(
                np.mean([d[4] for d in detections])
            ) if detections else 0.0

            return CaptchaSolution(
                success=True,
                solution=solution,
                solver_name=self.name,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"DarkNet solver error: {e}")
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

    def _preprocess(self, image) -> torch.Tensor:
        """Preprocess image for YOLO inference."""
        from PIL import Image

        # Resize to model input size
        image = image.convert("RGB")
        image = image.resize(
            (self.input_size, self.input_size), Image.LANCZOS
        )

        # Convert to tensor and normalize
        img_array = np.array(image).astype(np.float32) / 255.0
        # HWC -> CHW
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1)
        # Add batch dimension
        img_tensor = img_tensor.unsqueeze(0).to(self._device)

        return img_tensor

    def _detect(
        self, image
    ) -> List[Tuple[float, float, float, float, float, int]]:
        """
        Run object detection on the image.
        Returns list of (x1, y1, x2, y2, confidence, class_id).
        """
        # torch.no_grad() como context manager dentro del método (no decorador a
        # nivel de clase) para no evaluar torch al importar el módulo.
        with torch.no_grad():
            tensor = self._preprocess(image)
            outputs = self._model(tensor)

        # Process raw outputs into detections
        detections = self._process_output(outputs, image.size)

        # Apply NMS
        detections = self._nms(detections)

        return detections

    def _process_output(
        self, outputs, original_size: Tuple[int, int]
    ) -> List[Tuple[float, float, float, float, float, int]]:
        """Process model output into detection boxes."""
        detections = []
        orig_w, orig_h = original_size

        if isinstance(outputs, (list, tuple)):
            outputs = outputs[0]

        if hasattr(outputs, "cpu"):
            outputs = outputs.cpu().numpy()

        if outputs.ndim == 3:
            outputs = outputs[0]

        for detection in outputs:
            if len(detection) < 6:
                continue

            x_center, y_center, w, h = detection[:4]
            obj_conf = detection[4]
            class_scores = detection[5:]

            if obj_conf < self.confidence_threshold:
                continue

            class_id = int(np.argmax(class_scores))
            class_conf = class_scores[class_id]
            confidence = obj_conf * class_conf

            if confidence < self.confidence_threshold:
                continue

            # Convert to corner coordinates scaled to original
            scale_x = orig_w / self.input_size
            scale_y = orig_h / self.input_size

            x1 = (x_center - w / 2) * scale_x
            y1 = (y_center - h / 2) * scale_y
            x2 = (x_center + w / 2) * scale_x
            y2 = (y_center + h / 2) * scale_y

            detections.append(
                (x1, y1, x2, y2, float(confidence), class_id)
            )

        return detections


    def _nms(
        self,
        detections: List[Tuple[float, float, float, float, float, int]],
    ) -> List[Tuple[float, float, float, float, float, int]]:
        """Apply Non-Maximum Suppression to filter overlapping detections."""
        if not detections:
            return []

        # Sort by confidence descending
        detections = sorted(detections, key=lambda x: x[4], reverse=True)
        keep = []

        while detections:
            best = detections.pop(0)
            keep.append(best)

            remaining = []
            for det in detections:
                iou = self._compute_iou(best[:4], det[:4])
                if iou < self.nms_threshold:
                    remaining.append(det)
            detections = remaining

        return keep

    @staticmethod
    def _compute_iou(
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float],
    ) -> float:
        """Compute Intersection over Union between two boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _format_solution(
        self,
        detections: List[Tuple[float, float, float, float, float, int]],
        challenge: CaptchaChallenge,
    ) -> str:
        """
        Format detections into a solution string.
        For click captchas, returns center coordinates.
        """
        target_class = challenge.extra.get("target_class", None)

        if target_class is not None:
            detections = [
                d for d in detections if d[5] == target_class
            ]

        # Return center coordinates of each detection
        coordinates = []
        for x1, y1, x2, y2, conf, cls_id in detections:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            coordinates.append(f"{cx},{cy}")

        return "|".join(coordinates)
