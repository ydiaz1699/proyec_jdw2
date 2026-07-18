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

HOSTER_CAPTCHA_MAP = {
    "keep2share.cc": CaptchaType.TEXT_IMAGE,
    "k2s.cc": CaptchaType.TEXT_IMAGE,
    "fileboom.me": CaptchaType.TEXT_IMAGE,
    "fboom.me": CaptchaType.TEXT_IMAGE,
    "tezfiles.com": CaptchaType.TEXT_IMAGE,
    "publish2.me": CaptchaType.TEXT_IMAGE,
    "filejoker.net": CaptchaType.TEXT_IMAGE,
    "depositfiles.com": CaptchaType.TEXT_IMAGE,
    "dfiles.eu": CaptchaType.TEXT_IMAGE,
    "uploaded.net": CaptchaType.RECAPTCHA_V2,
    "uploadgig.com": CaptchaType.RECAPTCHA_V2,
    "nitroflare.com": CaptchaType.RECAPTCHA_V2,
    "mediafire.com": CaptchaType.HCAPTCHA,
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
        self._solvers.append((priority, solver))
        self._solvers.sort(key=lambda x: x[0])
        logger.info(f"Registered solver: {solver.name} (priority={priority})")

    def unregister_solver(self, name: str) -> bool:
        """Remove a solver by name. Returns True if it was found and removed."""
        before = len(self._solvers)
        self._solvers = [(p, s) for p, s in self._solvers if s.name != name]
        return len(self._solvers) != before

    def detect_type(self, challenge: CaptchaChallenge) -> CaptchaType:
        hoster = challenge.hoster.lower().strip()
        for known_hoster, ctype in HOSTER_CAPTCHA_MAP.items():
            if known_hoster in hoster:
                return ctype

        if challenge.image_data or challenge.image_base64:
            return CaptchaType.TEXT_IMAGE

        if challenge.site_key:
            extra_type = str(challenge.extra.get("type", "")).lower()
            if "recaptcha" in extra_type:
                return CaptchaType.RECAPTCHA_V2
            elif "hcaptcha" in extra_type:
                return CaptchaType.HCAPTCHA
            elif "turnstile" in extra_type:
                return CaptchaType.TURNSTILE
            return CaptchaType.RECAPTCHA_V2

        return CaptchaType.UNKNOWN

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        if challenge.captcha_type == CaptchaType.UNKNOWN:
            challenge.captcha_type = self.detect_type(challenge)

        logger.info(
            f"Solving captcha #{challenge.captcha_id} "
            f"(type={challenge.captcha_type.value}, hoster={challenge.hoster})"
        )

        suitable = [
            (p, s) for p, s in self._solvers
            if s.enabled and s.can_solve(challenge)
        ]

        if not suitable:
            return CaptchaSolution(
                success=False,
                error=f"No solver available for type: {challenge.captcha_type.value}",
            )

        for priority, solver in suitable:
            try:
                logger.debug(f"Trying solver: {solver.name}")
                solution = solver.solve(challenge)
                solver._record_attempt(solution)

                if solution.success:
                    preview = (solution.solution or "")[:20]
                    logger.info(
                        f"Solved by {solver.name}: "
                        f"'{preview}...' "
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
        return [s.stats for _, s in self._solvers]

    def get_solver(self, name: str) -> Optional[BaseSolver]:
        for _, s in self._solvers:
            if s.name == name:
                return s
        return None
