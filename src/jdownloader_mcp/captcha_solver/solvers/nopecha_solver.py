"""
NopeCHA Solver
==============
Solves captchas using the NopeCHA API (self-hosted or cloud).
Supports: reCAPTCHA v2/v3, hCaptcha, Turnstile, text/image captchas.

NopeCHA is an AI-based captcha solving service with optional self-hosted client.
"""

import base64
import logging
import time
from typing import Optional

import requests

from ..base import (
    BaseSolver,
    CaptchaChallenge,
    CaptchaSolution,
    CaptchaType,
)

logger = logging.getLogger("captcha-solver.nopecha")

NOPECHA_API_URL = "https://api.nopecha.com"
TIMEOUT_DEFAULT = 120
POLL_INTERVAL = 3


class NopeCHASolver(BaseSolver):
    """
    Solver that uses the NopeCHA API to solve various captcha types.
    Supports self-hosted inference endpoints.
    """

    name = "nopecha"
    supported_types = [
        CaptchaType.TEXT_IMAGE,
        CaptchaType.RECAPTCHA_V2,
        CaptchaType.RECAPTCHA_V3,
        CaptchaType.HCAPTCHA,
        CaptchaType.TURNSTILE,
    ]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_url = self.config.get("api_url", NOPECHA_API_URL)
        self.timeout = self.config.get("timeout", TIMEOUT_DEFAULT)
        self.poll_interval = self.config.get("poll_interval", POLL_INTERVAL)

        if not self.api_key:
            logger.warning("NopeCHA API key not configured - solver disabled")
            self.enabled = False

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a captcha challenge via NopeCHA API."""
        try:
            if challenge.captcha_type == CaptchaType.TEXT_IMAGE:
                return self._solve_image(challenge)
            else:
                return self._solve_token(challenge)

        except Exception as e:
            logger.error(f"NopeCHA error: {e}")
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=str(e),
            )

    def _solve_image(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a text/image captcha using NopeCHA recognition."""
        image_b64 = challenge.image_base64
        if not image_b64 and challenge.image_data:
            image_b64 = base64.b64encode(challenge.image_data).decode()

        if not image_b64:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="No image data provided",
            )

        payload = {
            "key": self.api_key,
            "type": "textcaptcha",
            "image_data": [image_b64],
        }

        try:
            resp = requests.post(
                f"{self.api_url}/",
                json=payload,
                timeout=30,
            )
            data = resp.json()

            if data.get("error"):
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"NopeCHA error: {data.get('message', data.get('error'))}",
                )

            answers = data.get("data", [])
            if answers:
                solution_text = str(answers[0])
                return CaptchaSolution(
                    success=True,
                    solution=solution_text,
                    solver_name=self.name,
                    confidence=0.90,
                )
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="NopeCHA returned no answers",
                )

        except requests.RequestException as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"NopeCHA request failed: {e}",
            )

    def _solve_token(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a token-based captcha (reCAPTCHA, hCaptcha, Turnstile)."""
        type_map = {
            CaptchaType.RECAPTCHA_V2: "recaptcha2",
            CaptchaType.RECAPTCHA_V3: "recaptcha3",
            CaptchaType.HCAPTCHA: "hcaptcha",
            CaptchaType.TURNSTILE: "turnstile",
        }

        task_type = type_map.get(challenge.captcha_type)
        if not task_type:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"Unsupported type: {challenge.captcha_type}",
            )

        payload = {
            "key": self.api_key,
            "type": task_type,
            "sitekey": challenge.site_key or "",
            "url": challenge.page_url or "",
        }

        if challenge.captcha_type == CaptchaType.RECAPTCHA_V3:
            payload["action"] = challenge.extra.get("action", "verify")
            payload["min_score"] = challenge.extra.get("min_score", 0.3)

        try:
            # Submit task
            resp = requests.post(
                f"{self.api_url}/token",
                json=payload,
                timeout=30,
            )
            data = resp.json()

            if data.get("error"):
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"NopeCHA error: {data.get('message', data.get('error'))}",
                )

            # If we got a token directly
            token = data.get("data")
            if token:
                return CaptchaSolution(
                    success=True,
                    solution=str(token),
                    solver_name=self.name,
                    confidence=0.92,
                )

            # If we got a job ID, poll for result
            job_id = data.get("id")
            if job_id:
                return self._poll_token_result(job_id)

            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="NopeCHA returned unexpected response",
            )

        except requests.RequestException as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"NopeCHA request failed: {e}",
            )

    def _poll_token_result(self, job_id: str) -> CaptchaSolution:
        """Poll NopeCHA for a token result."""
        deadline = time.time() + self.timeout

        while time.time() < deadline:
            time.sleep(self.poll_interval)

            try:
                resp = requests.get(
                    f"{self.api_url}/token",
                    params={"key": self.api_key, "id": job_id},
                    timeout=30,
                )
                data = resp.json()

                if data.get("error"):
                    error_msg = data.get("message", data.get("error"))
                    if "processing" in str(error_msg).lower():
                        continue
                    return CaptchaSolution(
                        success=False,
                        solver_name=self.name,
                        error=f"NopeCHA error: {error_msg}",
                    )

                token = data.get("data")
                if token:
                    return CaptchaSolution(
                        success=True,
                        solution=str(token),
                        solver_name=self.name,
                        confidence=0.92,
                    )

            except requests.RequestException as e:
                logger.debug(f"NopeCHA poll error: {e}")
                continue

        return CaptchaSolution(
            success=False,
            solver_name=self.name,
            error=f"NopeCHA job {job_id} timed out",
        )
