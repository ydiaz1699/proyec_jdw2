"""
Captcha Router - Detects captcha type and routes to the best solver.
"""

import logging
from typing import List, Optional

from .base import (
    BaseSolver,
    CaptchaChallenge,
    CaptchaSolution,
    CaptchaType,
)

logger = logging.getLogger("captcha-solver.router")

# Known hosters and their typical captcha types
HOSTER_CAPTCHA_MAP = {
    # Text/image captchas
    "keep2share.cc": CaptchaType.TEXT_IMAGE,
    "k2s.cc": CaptchaType.TEXT_IMAGE,
    "fileboom.me": CaptchaType.TEXT_IMAGE,
    "fboom.me": CaptchaType.TEXT_IMAGE,
    "tezfiles.com": CaptchaType.TEXT_IMAGE,
    "publish2.me": CaptchaType.TEXT_IMAGE,
    "filejoker.net": CaptchaType.TEXT_IMAGE,
    "depositfiles.com": CaptchaType.TEXT_IMAGE,
    "dfiles.eu": CaptchaType.TEXT_IMAGE,
    # reCAPTCHA hosters
    "uploaded.net": CaptchaType.RECAPTCHA_V2,
    "uploadgig.com": CaptchaType.RECAPTCHA_V2,
    "nitroflare.com": CaptchaType.RECAPTCHA_V2,
    # hCaptcha hosters
    "mediafire.com": CaptchaType.HCAPTCHA,
    # Cloudflare Turnstile
    "rapidgator.net": CaptchaType.TURNSTILE,
    "katfile.com": CaptchaType.TURNSTILE,
}


class CaptchaRouter:
    """
    Routes captcha challenges to the appropriate solver.
    Maintains a priority-ordered list of solvers and tries them
    in order until one succeeds.
    """

    def __init__(self):
        self._solvers: List[BaseSolver] = []

    def register_solver(self, solver: BaseSolver, priority: int = 100):
        """
        Register a solver with a priority (lower = higher priority).

        Args:
            solver: Solver instance to register
            priority: Priority order (0 = highest, 999 = lowest)
        """
        self._solvers.append((priority, solver))
        self._solvers.sort(key=lambda x: x[0])
        logger.info(f"Registered solver: {solver.name} (priority={priority})")

    def detect_type(self, challenge: CaptchaChallenge) -> CaptchaType:
        """
        Detect the captcha type from the challenge data.

        Uses hoster mapping first, then analyzes the image if available.
        """
        # Check hoster map
        hoster = challenge.hoster.lower().strip()
        for known_hoster, ctype in HOSTER_CAPTCHA_MAP.items():
            if known_hoster in hoster:
                return ctype

        # If we have image data, it's likely a text/image captcha
        if challenge.image_data or challenge.image_base64:
            return CaptchaType.TEXT_IMAGE

        # If we have a site_key, it's a token-based captcha
        if challenge.site_key:
            if "recaptcha" in challenge.extra.get("type", "").lower():
                return CaptchaType.RECAPTCHA_V2
            elif "hcaptcha" in challenge.extra.get("type", "").lower():
                return CaptchaType.HCAPTCHA
            elif "turnstile" in challenge.extra.get("type", "").lower():
                return CaptchaType.TURNSTILE
            return CaptchaType.RECAPTCHA_V2  # default for site_key

        return CaptchaType.UNKNOWN

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Route a challenge to the best available solver.

        Tries solvers in priority order. Falls back to the next solver
        if one fails.
        """
        # Detect type if not already set
        if challenge.captcha_type == CaptchaType.UNKNOWN:
            challenge.captcha_type = self.detect_type(challenge)

        logger.info(
            f"Solving captcha #{challenge.captcha_id} "
            f"(type={challenge.captcha_type.value}, hoster={challenge.hoster})"
        )

        # Find suitable solvers
        suitable = [
            (p, s) for p, s in self._solvers
            if s.enabled and s.can_solve(challenge)
        ]

        if not suitable:
            return CaptchaSolution(
                success=False,
                error=f"No solver available for type: {challenge.captcha_type.value}",
            )

        # Try each solver in priority order
        for priority, solver in suitable:
            try:
                logger.debug(f"Trying solver: {solver.name}")
                solution = solver.solve(challenge)
                solver._record_attempt(solution)

                if solution.success:
                    logger.info(
                        f"Solved by {solver.name}: "
                        f"'{solution.solution[:20]}...' "
                        f"(confidence={solution.confidence:.1%})"
                    )
                    return solution
                else:
                    logger.debug(
                        f"Solver {solver.name} failed: {solution.error}"
                    )
            except Exception as e:
                logger.error(f"Solver {solver.name} error: {e}")
                solver._record_attempt(CaptchaSolution(success=False, error=str(e)))

        return CaptchaSolution(
            success=False,
            error="All solvers failed",
        )

    @property
    def solvers(self) -> list:
        """Get list of registered solvers with stats."""
        return [s.stats for _, s in self._solvers]

    def get_solver(self, name: str) -> Optional[BaseSolver]:
        """Get a solver by name."""
        for _, s in self._solvers:
            if s.name == name:
                return s
        return None
