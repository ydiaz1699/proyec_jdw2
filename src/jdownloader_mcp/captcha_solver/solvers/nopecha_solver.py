"""
NopeCHA API Solver - Token-based captcha solver via NopeCHA's HTTP API.
========================================================================
Self-contained HTTP client — does NOT depend on NopeCHA's Python/Node library.
Implements the Recognition and Token API endpoints directly.

Supports:
- reCAPTCHA v2/v3
- hCaptcha
- Cloudflare Turnstile
- FunCAPTCHA
- AWS WAF
- Text/image captchas (as fallback)

Usage:
    solver = NopeCHASolver(config={"api_key": "your_key"})
    solution = solver.solve(challenge)

API docs: https://developers.nopecha.com/
Free tier: 100 requests/day without API key (IP-based)
"""

import json
import time
import logging
from typing import Optional

import requests

from ..base import BaseSolver, CaptchaChallenge, CaptchaSolution, CaptchaType

logger = logging.getLogger("captcha-solver.nopecha")

NOPECHA_API_URL = "https://api.nopecha.com"
NOPECHA_RECOGNITION_URL = f"{NOPECHA_API_URL}/recognition"
NOPECHA_TOKEN_URL = f"{NOPECHA_API_URL}/token"


class NopeCHASolver(BaseSolver):
    """
    Solves captchas via the NopeCHA API.

    Config options:
        api_key: NopeCHA API key (optional, free tier uses IP-based limits)
        timeout: Request timeout in seconds (default: 120)
        poll_interval: Seconds between polling for result (default: 5)
        max_polls: Maximum poll attempts (default: 24 = 2 minutes)

    Supports all token-based captchas (reCAPTCHA, hCaptcha, Turnstile)
    and image recognition captchas.
    """

    name = "nopecha_api"
    supported_types = [
        CaptchaType.RECAPTCHA_V2,
        CaptchaType.RECAPTCHA_V3,
        CaptchaType.HCAPTCHA,
        CaptchaType.TURNSTILE,
        CaptchaType.FUNCAPTCHA,
        CaptchaType.AWS_WAF,
        CaptchaType.TEXT_IMAGE,
    ]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)

        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 120)
        self.poll_interval = self.config.get("poll_interval", 5)
        self.max_polls = self.config.get("max_polls", 24)

        if not self.api_key:
            logger.info(
                "NopeCHA solver: No API key set. Using free tier (100 req/day by IP). "
                "Set config['api_key'] for higher limits."
            )

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Route to the appropriate NopeCHA endpoint based on captcha type."""
        try:
            if challenge.captcha_type in (
                CaptchaType.RECAPTCHA_V2,
                CaptchaType.RECAPTCHA_V3,
                CaptchaType.HCAPTCHA,
                CaptchaType.TURNSTILE,
                CaptchaType.FUNCAPTCHA,
                CaptchaType.AWS_WAF,
            ):
                return self._solve_token(challenge)
            elif challenge.captcha_type == CaptchaType.TEXT_IMAGE:
                return self._solve_recognition(challenge)
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error=f"Unsupported type: {challenge.captcha_type.value}",
                )
        except requests.exceptions.RequestException as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"Network error: {e}",
            )
        except Exception as e:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"NopeCHA error: {e}",
            )

    def _solve_token(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Solve token-based captchas (reCAPTCHA, hCaptcha, Turnstile, etc.).
        Uses the /token endpoint with polling.
        """
        # Map our types to NopeCHA type names
        type_map = {
            CaptchaType.RECAPTCHA_V2: "recaptcha2",
            CaptchaType.RECAPTCHA_V3: "recaptcha3",
            CaptchaType.HCAPTCHA: "hcaptcha",
            CaptchaType.TURNSTILE: "turnstile",
            CaptchaType.FUNCAPTCHA: "funcaptcha",
            CaptchaType.AWS_WAF: "awscaptcha",
        }

        captcha_type = type_map.get(challenge.captcha_type, "recaptcha2")

        # Build request payload
        payload = {
            "type": captcha_type,
            "sitekey": challenge.site_key or "",
            "url": challenge.page_url or "",
        }

        if self.api_key:
            payload["key"] = self.api_key

        # Additional fields for specific types
        if challenge.captcha_type == CaptchaType.RECAPTCHA_V3:
            payload["action"] = challenge.extra.get("action", "verify")
            payload["min_score"] = challenge.extra.get("min_score", 0.5)

        # Submit task
        logger.debug(f"NopeCHA token request: type={captcha_type}")
        response = requests.post(
            NOPECHA_TOKEN_URL,
            json=payload,
            timeout=30,
        )

        data = response.json()

        if "error" in data:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"NopeCHA error: {data['error']}",
            )

        # If we got a token directly
        if "data" in data and data["data"]:
            return CaptchaSolution(
                success=True,
                solution=data["data"],
                solver_name=self.name,
                confidence=0.9,
            )

        # Poll for result if we got a job ID
        job_id = data.get("data") or data.get("id")
        if not job_id:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="No job ID or token returned",
            )

        return self._poll_result(job_id)

    def _solve_recognition(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """
        Solve image recognition captchas using the /recognition endpoint.
        Sends the image and receives the text answer.
        """
        if not challenge.image_base64:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error="No image data for recognition",
            )

        payload = {
            "type": "textcaptcha",
            "image_data": [challenge.image_base64],
        }

        if self.api_key:
            payload["key"] = self.api_key

        response = requests.post(
            NOPECHA_RECOGNITION_URL,
            json=payload,
            timeout=30,
        )

        data = response.json()

        if "error" in data:
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=f"NopeCHA recognition error: {data['error']}",
            )

        # Recognition returns the answer directly
        answers = data.get("data", [])
        if answers and isinstance(answers, list) and answers[0]:
            return CaptchaSolution(
                success=True,
                solution=answers[0],
                solver_name=self.name,
                confidence=0.85,
            )

        return CaptchaSolution(
            success=False,
            solver_name=self.name,
            error="NopeCHA returned empty recognition result",
        )

    def _poll_result(self, job_id: str) -> CaptchaSolution:
        """Poll NopeCHA for a token result."""
        for attempt in range(self.max_polls):
            time.sleep(self.poll_interval)

            try:
                payload = {"id": job_id}
                if self.api_key:
                    payload["key"] = self.api_key

                response = requests.get(
                    f"{NOPECHA_TOKEN_URL}",
                    params=payload,
                    timeout=30,
                )
                data = response.json()

                if "error" in data:
                    if "processing" in str(data["error"]).lower():
                        continue  # Still working
                    return CaptchaSolution(
                        success=False,
                        solver_name=self.name,
                        error=f"NopeCHA poll error: {data['error']}",
                    )

                if "data" in data and data["data"]:
                    return CaptchaSolution(
                        success=True,
                        solution=data["data"],
                        solver_name=self.name,
                        confidence=0.9,
                    )

            except requests.exceptions.RequestException:
                continue

        return CaptchaSolution(
            success=False,
            solver_name=self.name,
            error=f"Timeout after {self.max_polls * self.poll_interval}s",
        )

    def get_balance(self) -> dict:
        """Check NopeCHA API credit balance."""
        if not self.api_key:
            return {"error": "No API key set", "plan": "free (100/day by IP)"}
        try:
            response = requests.get(
                f"{NOPECHA_API_URL}/status",
                params={"key": self.api_key},
                timeout=10,
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
