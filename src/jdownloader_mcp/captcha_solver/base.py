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
    TEXT_IMAGE = "text_image"
    GEOMETRIC = "geometric"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"
    FUNCAPTCHA = "funcaptcha"
    AWS_WAF = "aws_waf"
    UNKNOWN = "unknown"


@dataclass
class CaptchaChallenge:
    """Represents a captcha challenge from JDownloader."""
    captcha_id: int
    hoster: str = ""
    captcha_type: CaptchaType = CaptchaType.UNKNOWN
    image_data: Optional[bytes] = None
    image_base64: Optional[str] = None
    site_key: Optional[str] = None
    page_url: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class CaptchaSolution:
    """Result from a solver attempt."""
    success: bool
    solution: Optional[str] = None
    solver_name: str = ""
    confidence: float = 0.0
    error: Optional[str] = None


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
        pass

    def can_solve(self, challenge: CaptchaChallenge) -> bool:
        return challenge.captcha_type in self.supported_types

    @property
    def success_rate(self) -> float:
        total = self._stats["attempts"]
        if total == 0:
            return 0.0
        return self._stats["successes"] / total

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "attempts": self._stats["attempts"],
            "successes": self._stats["successes"],
            "failures": self._stats["failures"],
            "success_rate": f"{self.success_rate:.1%}",
        }

    def _record_attempt(self, solution: CaptchaSolution):
        self._stats["attempts"] += 1
        if solution.success:
            self._stats["successes"] += 1
        else:
            self._stats["failures"] += 1
