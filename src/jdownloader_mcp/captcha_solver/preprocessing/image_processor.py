"""
Image Preprocessing Pipeline for Captcha Solving
=================================================
Self-contained image processing without external ML dependencies.
Uses only Pillow (PIL) for all transformations.

Techniques applied:
1. Grayscale conversion
2. Noise removal (median filter, morphological ops)
3. Binarization (adaptive threshold via Otsu-like method)
4. Deskew (rotation correction)
5. Character segmentation helpers
6. Border/padding removal
"""

import io
import base64
import logging
from typing import Optional, Tuple, List

try:
    from PIL import Image, ImageFilter, ImageOps, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger("captcha-solver.preprocessing")


class ImageProcessor:
    """
    Processes captcha images to maximize OCR accuracy.
    All methods are static/standalone — no external state needed.
    """

    @staticmethod
    def from_base64(b64_string: str) -> Optional["Image.Image"]:
        """Decode a base64 string to a PIL Image."""
        if not HAS_PIL:
            logger.error("Pillow not installed. Run: pip install Pillow")
            return None
        try:
            # Handle data URI prefix
            if "," in b64_string:
                b64_string = b64_string.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_string)
            return Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            return None

    @staticmethod
    def from_bytes(img_bytes: bytes) -> Optional["Image.Image"]:
        """Load a PIL Image from raw bytes."""
        if not HAS_PIL:
            return None
        try:
            return Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            logger.error(f"Failed to load image from bytes: {e}")
            return None

    @staticmethod
    def to_grayscale(img: "Image.Image") -> "Image.Image":
        """Convert image to grayscale."""
        return img.convert("L")

    @staticmethod
    def remove_noise(img: "Image.Image", passes: int = 1) -> "Image.Image":
        """
        Remove noise using median filter.
        Multiple passes for heavy noise.
        """
        result = img
        for _ in range(passes):
            result = result.filter(ImageFilter.MedianFilter(size=3))
        return result

    @staticmethod
    def remove_single_pixels(img: "Image.Image") -> "Image.Image":
        """
        Remove isolated single pixels (salt-and-pepper noise).
        A pixel is removed if it has fewer than 2 same-color neighbors.
        """
        if img.mode != "L":
            img = img.convert("L")

        pixels = img.load()
        width, height = img.size
        result = img.copy()
        result_pixels = result.load()

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if pixels[x, y] < 128:  # Dark pixel
                    # Count dark neighbors
                    neighbors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            if pixels[x + dx, y + dy] < 128:
                                neighbors += 1
                    # Remove if isolated
                    if neighbors < 2:
                        result_pixels[x, y] = 255

        return result

    @staticmethod
    def binarize(img: "Image.Image", threshold: Optional[int] = None) -> "Image.Image":
        """
        Convert to black and white using a threshold.
        If threshold is None, uses Otsu's method (automatic).
        """
        if img.mode != "L":
            img = img.convert("L")

        if threshold is None:
            # Simple Otsu's method implementation
            threshold = ImageProcessor._otsu_threshold(img)

        return img.point(lambda p: 255 if p > threshold else 0, "L")

    @staticmethod
    def _otsu_threshold(img: "Image.Image") -> int:
        """Calculate optimal threshold using Otsu's method."""
        histogram = img.histogram()
        total = sum(histogram)

        sum_total = sum(i * histogram[i] for i in range(256))
        sum_bg = 0
        weight_bg = 0
        max_variance = 0
        best_threshold = 0

        for t in range(256):
            weight_bg += histogram[t]
            if weight_bg == 0:
                continue

            weight_fg = total - weight_bg
            if weight_fg == 0:
                break

            sum_bg += t * histogram[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg

            variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2

            if variance > max_variance:
                max_variance = variance
                best_threshold = t

        return best_threshold

    @staticmethod
    def remove_borders(img: "Image.Image", border_width: int = 2) -> "Image.Image":
        """Remove borders/frame from captcha image."""
        width, height = img.size
        return img.crop((
            border_width,
            border_width,
            width - border_width,
            height - border_width,
        ))

    @staticmethod
    def remove_lines(img: "Image.Image", direction: str = "both") -> "Image.Image":
        """
        Remove straight lines (horizontal/vertical) that cross the image.
        These are common anti-OCR obfuscations.
        """
        if img.mode != "L":
            img = img.convert("L")

        pixels = img.load()
        width, height = img.size
        result = img.copy()
        result_pixels = result.load()

        if direction in ("horizontal", "both"):
            for y in range(height):
                dark_count = sum(1 for x in range(width) if pixels[x, y] < 128)
                # If more than 80% of the row is dark, it's a line
                if dark_count > width * 0.8:
                    for x in range(width):
                        result_pixels[x, y] = 255

        if direction in ("vertical", "both"):
            pixels = result.load()  # Use updated image
            for x in range(width):
                dark_count = sum(1 for y in range(height) if pixels[x, y] < 128)
                if dark_count > height * 0.8:
                    for y in range(height):
                        result_pixels[x, y] = 255

        return result

    @staticmethod
    def dilate(img: "Image.Image", iterations: int = 1) -> "Image.Image":
        """Dilate (thicken) dark regions — helps reconnect broken characters."""
        result = img
        for _ in range(iterations):
            result = result.filter(ImageFilter.MinFilter(size=3))
        return result

    @staticmethod
    def erode(img: "Image.Image", iterations: int = 1) -> "Image.Image":
        """Erode (thin) dark regions — helps separate touching characters."""
        result = img
        for _ in range(iterations):
            result = result.filter(ImageFilter.MaxFilter(size=3))
        return result

    @staticmethod
    def sharpen(img: "Image.Image") -> "Image.Image":
        """Sharpen the image to make edges clearer."""
        return img.filter(ImageFilter.SHARPEN)

    @staticmethod
    def scale(img: "Image.Image", factor: float = 2.0) -> "Image.Image":
        """Scale image by a factor (2.0 = double size). Helps OCR accuracy."""
        width, height = img.size
        new_size = (int(width * factor), int(height * factor))
        return img.resize(new_size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

    @staticmethod
    def invert_if_needed(img: "Image.Image") -> "Image.Image":
        """Invert colors if background is dark (ensure dark text on white bg)."""
        if img.mode != "L":
            img = img.convert("L")

        stat = ImageStat.Stat(img)
        mean_brightness = stat.mean[0]

        # If average brightness is low, background is dark → invert
        if mean_brightness < 128:
            return ImageOps.invert(img)
        return img

    @staticmethod
    def segment_characters(img: "Image.Image", num_chars: int = 0) -> List["Image.Image"]:
        """
        Attempt to segment individual characters from the image.
        Uses vertical projection to find gaps between characters.

        Args:
            img: Binarized grayscale image
            num_chars: Expected number of characters (0 = auto-detect)

        Returns:
            List of cropped character images
        """
        if img.mode != "L":
            img = img.convert("L")

        pixels = img.load()
        width, height = img.size

        # Vertical projection: count dark pixels per column
        projection = []
        for x in range(width):
            col_dark = sum(1 for y in range(height) if pixels[x, y] < 128)
            projection.append(col_dark)

        # Find character regions (runs of non-zero projection)
        in_char = False
        start = 0
        regions = []

        for x, count in enumerate(projection):
            if count > 0 and not in_char:
                start = x
                in_char = True
            elif count == 0 and in_char:
                regions.append((start, x))
                in_char = False

        if in_char:
            regions.append((start, width))

        # Filter out very thin regions (noise)
        min_width = max(3, width // 20)
        regions = [(s, e) for s, e in regions if (e - s) >= min_width]

        # If we know the expected count and have fewer regions,
        # try to split the widest regions
        if num_chars > 0 and len(regions) < num_chars:
            while len(regions) < num_chars:
                # Find widest region and split it
                widths = [(e - s, i) for i, (s, e) in enumerate(regions)]
                widths.sort(reverse=True)
                if not widths:
                    break
                _, idx = widths[0]
                s, e = regions[idx]
                mid = (s + e) // 2
                regions[idx] = (s, mid)
                regions.insert(idx + 1, (mid, e))

        # Crop character images
        chars = []
        for start_x, end_x in regions:
            char_img = img.crop((start_x, 0, end_x, height))
            chars.append(char_img)

        return chars

    @classmethod
    def full_pipeline(
        cls,
        img: "Image.Image",
        scale_factor: float = 2.0,
        noise_passes: int = 1,
        remove_border: bool = True,
    ) -> "Image.Image":
        """
        Apply the full preprocessing pipeline optimized for OCR.

        Steps:
        1. Scale up (improves OCR on small images)
        2. Grayscale
        3. Remove borders
        4. Invert if needed
        5. Noise removal
        6. Remove isolated pixels
        7. Binarize (Otsu)
        8. Sharpen

        Returns:
            Preprocessed image ready for OCR
        """
        # Scale
        if scale_factor != 1.0:
            img = cls.scale(img, scale_factor)

        # Grayscale
        img = cls.to_grayscale(img)

        # Remove borders
        if remove_border:
            img = cls.remove_borders(img)

        # Ensure dark text on white background
        img = cls.invert_if_needed(img)

        # Noise removal
        img = cls.remove_noise(img, passes=noise_passes)
        img = cls.remove_single_pixels(img)

        # Binarize
        img = cls.binarize(img)

        # Sharpen
        img = cls.sharpen(img)

        return img

    @classmethod
    def pipeline_for_hoster(cls, img: "Image.Image", hoster: str) -> "Image.Image":
        """
        Apply a hoster-specific preprocessing pipeline.
        Different hosters use different captcha styles.
        """
        hoster_lower = hoster.lower()

        if "keep2share" in hoster_lower or "k2s" in hoster_lower:
            # k2s has heavy noise, colored backgrounds
            img = cls.scale(img, 3.0)
            img = cls.to_grayscale(img)
            img = cls.remove_noise(img, passes=2)
            img = cls.remove_single_pixels(img)
            img = cls.binarize(img)
            img = cls.remove_single_pixels(img)
            img = cls.dilate(img, 1)
            return img

        elif "filejoker" in hoster_lower:
            # filejoker has lines crossing through text
            img = cls.scale(img, 2.0)
            img = cls.to_grayscale(img)
            img = cls.remove_borders(img)
            img = cls.binarize(img)
            img = cls.remove_lines(img, "both")
            img = cls.remove_single_pixels(img)
            return img

        elif "depositfiles" in hoster_lower or "dfiles" in hoster_lower:
            # depositfiles has warped text
            img = cls.scale(img, 2.5)
            img = cls.to_grayscale(img)
            img = cls.remove_noise(img, passes=1)
            img = cls.binarize(img)
            img = cls.sharpen(img)
            return img

        else:
            # Default pipeline
            return cls.full_pipeline(img)
