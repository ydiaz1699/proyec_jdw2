"""
Image Processor
===============
Preprocessing pipeline for captcha images before solving.
Handles noise removal, normalization, segmentation, and enhancement.

Requires:
- Pillow >= 10.0.0
"""

import io
import logging
from typing import Optional, Tuple

from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger("captcha-solver.preprocessing")


class ImageProcessor:
    """
    Image preprocessing pipeline for captcha images.
    Applies various transformations to improve solver accuracy.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.target_size: Optional[Tuple[int, int]] = self.config.get(
            "target_size", None
        )
        self.grayscale: bool = self.config.get("grayscale", True)
        self.threshold: Optional[int] = self.config.get("threshold", None)
        self.denoise: bool = self.config.get("denoise", True)
        self.sharpen: bool = self.config.get("sharpen", True)
        self.remove_border: bool = self.config.get("remove_border", False)
        self.invert: bool = self.config.get("invert", False)


    def process(self, image: Image.Image) -> Image.Image:
        """
        Apply the full preprocessing pipeline to an image.

        Args:
            image: PIL Image to process.

        Returns:
            Processed PIL Image.
        """
        # Convert to RGB first for consistent processing
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB" and not self.grayscale:
            image = image.convert("RGB")

        # Grayscale conversion
        if self.grayscale:
            image = image.convert("L")

        # Remove border/frame
        if self.remove_border:
            image = self._remove_border(image)

        # Denoise
        if self.denoise:
            image = self._denoise(image)

        # Sharpen
        if self.sharpen:
            image = self._sharpen(image)

        # Binary threshold
        if self.threshold is not None:
            image = self._threshold(image, self.threshold)

        # Invert colors
        if self.invert:
            image = ImageOps.invert(image)

        # Resize to target size
        if self.target_size:
            image = self._resize(image, self.target_size)

        return image

    def process_bytes(self, image_data: bytes) -> Image.Image:
        """Process raw image bytes through the pipeline."""
        image = Image.open(io.BytesIO(image_data))
        return self.process(image)


    def _denoise(self, image: Image.Image) -> Image.Image:
        """Remove noise using median filter."""
        return image.filter(ImageFilter.MedianFilter(size=3))

    def _sharpen(self, image: Image.Image) -> Image.Image:
        """Sharpen the image to make text clearer."""
        return image.filter(ImageFilter.SHARPEN)

    def _threshold(self, image: Image.Image, value: int) -> Image.Image:
        """Apply binary threshold to the image."""
        if image.mode != "L":
            image = image.convert("L")
        return image.point(lambda p: 255 if p > value else 0)

    def _resize(
        self, image: Image.Image, target: Tuple[int, int]
    ) -> Image.Image:
        """Resize image to target dimensions."""
        return image.resize(target, Image.LANCZOS)

    def _remove_border(
        self, image: Image.Image, border_px: int = 2
    ) -> Image.Image:
        """Remove border pixels from the image."""
        w, h = image.size
        if w <= border_px * 2 or h <= border_px * 2:
            return image
        return image.crop((
            border_px, border_px,
            w - border_px, h - border_px,
        ))

    @staticmethod
    def remove_lines(image: Image.Image) -> Image.Image:
        """
        Attempt to remove straight lines (common captcha noise).
        Works best on binary/grayscale images.
        """
        if image.mode != "L":
            image = image.convert("L")

        # Use erosion to remove thin lines
        from PIL import ImageMorph

        try:
            # Horizontal line removal
            lut = ImageMorph.LutBuilder(
                patterns=["1:(0,0,0,1,1,1,0,0,0)->0"]
            ).build_lut()
            _, image = ImageMorph.MorphOp(lut=lut).apply(image)
        except Exception:
            # Fallback: just apply min filter
            image = image.filter(ImageFilter.MinFilter(size=3))

        return image

    @staticmethod
    def auto_crop(image: Image.Image, padding: int = 5) -> Image.Image:
        """
        Auto-crop the image to the bounding box of non-white content.
        """
        if image.mode != "L":
            gray = image.convert("L")
        else:
            gray = image

        # Find bounding box of content
        bbox = gray.getbbox()
        if bbox is None:
            return image

        x1, y1, x2, y2 = bbox
        # Add padding
        w, h = image.size
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)

        return image.crop((x1, y1, x2, y2))
