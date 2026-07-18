"""
Base classes for captcha solvers.
All solvers must inherit from BaseSolver.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("captcha-solver")


class CaptchaType(Enum):
    """Types of captchas that JDownloader can encounter."""
    TEXT_IMAGE = "text_image"           # Simple text in image (4-6 chars)
    GEOMETRIC = "geometric"             # Geometric shapes (keep2share new)
    RECAPTCHA_V2 = "recaptcha_v2"       # Google reCAPTCHA v2
    RECAPTCHA_V3 = "recaptcha_v3"       # Google reCAPTCHA v3 (invisible)
    HCAPTCHA = "hcaptcha"               # hCaptcha image selection
    TURNSTILE = "turnstile"             # Cloudflare Turnstile
    FUNCAPTCHA = "funcaptcha"           # FunCAPTCHA / Arkose Labs
    AWS_WAF = "aws_waf"                 # AWS WAF CAPTCHA
    UNKNOWN = "unknown"                 # Unrecognized type


@dataclass
class CaptchaChallenge:
    """Represents a captcha challenge from JDownloader."""
    captcha_id: int
    hoster: str = ""
    captcha_type: CaptchaType = CaptchaType.UNKNOWN
    image_data: Optional[bytes] = None   # Raw image bytes (for image captchas)
    image_base64: Optional[str] = None   # Base64 encoded image
    site_key: Optional[str] = None       # Site key (for reCAPTCHA/hCaptcha)
    page_url: Optional[str] = None       # Page URL (for token-based captchas)
    extra: dict = field(default_factory=dict)


@dataclass
class CaptchaSolution:
    """Result from a solver attempt."""
    success: bool
    solution: Optional[str] = None       # The answer text or token
    solver_name: str = ""                # Which solver produced this
    confidence: float = 0.0              # 0.0 to 1.0
    error: Optional[str] = None          # Error message if failed


class BaseSolver(ABC):
    """Abstract base class for all captcha solvers."""

    name: str = "base"
    supported_types: list = []

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.enabled = True
        self._stats = {"attempts": 0, "successes": 0, "failures": 0}

    @abstractmethod
    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Attempt to solve a captcha challenge.

        Args:
            challenge: The captcha challenge to solve

        Returns:
            CaptchaSolution with the result
        """
        pass

    def can_solve(self, challenge: CaptchaChallenge) -> bool:
        """Check if this solver can handle the given challenge type."""
        return challenge.captcha_type in self.supported_types

    @property
    def success_rate(self) -> float:
        """Get the solver's success rate."""
        total = self._stats["attempts"]
        if total == 0:
            return 0.0
        return self._stats["successes"] / total

    @property
    def stats(self) -> dict:
        """Get solver statistics."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "attempts": self._stats["attempts"],
            "successes": self._stats["successes"],
            "failures": self._stats["failures"],
            "success_rate": f"{self.success_rate:.1%}",
        }

    def _record_attempt(self, solution: CaptchaSolution):
        """Record an attempt for statistics."""
        self._stats["attempts"] += 1
        if solution.success:
            self._stats["successes"] += 1
        else:
            self._stats["failures"] += 1
