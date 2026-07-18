"""
2Captcha Solver
===============
Solves captchas using the 2Captcha API service.
Supports: reCAPTCHA v2/v3, hCaptcha, Turnstile, FunCaptcha, text/image captchas.

Requires a 2Captcha API key (paid service).
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

logger = logging.getLogger("captcha-solver.twocaptcha")

API_BASE = "https://2captcha.com"
TIMEOUT_DEFAULT = 120
POLL_INTERVAL = 5


class TwoCaptchaSolver(BaseSolver):
    """
    Solver that uses the 2Captcha API to solve various captcha types.
    """

    name = "2captcha"
    supported_types = [
        CaptchaType.TEXT_IMAGE,
        CaptchaType.RECAPTCHA_V2,
        CaptchaType.RECAPTCHA_V3,
        CaptchaType.HCAPTCHA,
        CaptchaType.TURNSTILE,
        CaptchaType.FUNCAPTCHA,
    ]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", TIMEOUT_DEFAULT)
        self.poll_interval = self.config.get("poll_interval", POLL_INTERVAL)

        if not self.api_key:
            logger.warning("2Captcha API key not configured - solver disabled")
            self.enabled = False

    def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """Solve a captcha challenge via 2Captcha API."""
        try:
            task_id = self._create_task(challenge)
            if not task_id:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="Failed to create 2Captcha task",
                )

            solution = self._poll_result(task_id)
            if solution:
                return CaptchaSolution(
                    success=True,
                    solution=solution,
                    solver_name=self.name,
                    confidence=0.95,
                )
            else:
                return CaptchaSolution(
                    success=False,
                    solver_name=self.name,
                    error="2Captcha task timed out or failed",
                )

        except Exception as e:
            logger.error(f"2Captcha error: {e}")
            return CaptchaSolution(
                success=False,
                solver_name=self.name,
                error=str(e),
            )

    def _create_task(self, challenge: CaptchaChallenge) -> Optional[str]:
        """Submit captcha to 2Captcha and return task ID."""
        params = {
            "key": self.api_key,
            "json": 1,
        }

        if challenge.captcha_type == CaptchaType.TEXT_IMAGE:
            params["method"] = "base64"
            if challenge.image_base64:
                params["body"] = challenge.image_base64
            elif challenge.image_data:
                params["body"] = base64.b64encode(challenge.image_data).decode()
            else:
                return None

        elif challenge.captcha_type == CaptchaType.RECAPTCHA_V2:
            params["method"] = "userrecaptcha"
            params["googlekey"] = challenge.site_key or ""
            params["pageurl"] = challenge.page_url or ""

        elif challenge.captcha_type == CaptchaType.RECAPTCHA_V3:
            params["method"] = "userrecaptcha"
            params["version"] = "v3"
            params["googlekey"] = challenge.site_key or ""
            params["pageurl"] = challenge.page_url or ""
            params["action"] = challenge.extra.get("action", "verify")
            params["min_score"] = challenge.extra.get("min_score", 0.3)

        elif challenge.captcha_type == CaptchaType.HCAPTCHA:
            params["method"] = "hcaptcha"
            params["sitekey"] = challenge.site_key or ""
            params["pageurl"] = challenge.page_url or ""

        elif challenge.captcha_type == CaptchaType.TURNSTILE:
            params["method"] = "turnstile"
            params["sitekey"] = challenge.site_key or ""
            params["pageurl"] = challenge.page_url or ""

        elif challenge.captcha_type == CaptchaType.FUNCAPTCHA:
            params["method"] = "funcaptcha"
            params["publickey"] = challenge.site_key or ""
            params["pageurl"] = challenge.page_url or ""

        else:
            logger.warning(f"Unsupported type for 2Captcha: {challenge.captcha_type}")
            return None

        try:
            resp = requests.post(f"{API_BASE}/in.php", data=params, timeout=30)
            data = resp.json()

            if data.get("status") == 1:
                task_id = str(data.get("request"))
                logger.debug(f"2Captcha task created: {task_id}")
                return task_id
            else:
                logger.error(f"2Captcha submit error: {data.get('request')}")
                return None

        except requests.RequestException as e:
            logger.error(f"2Captcha API request failed: {e}")
            return None

    def _poll_result(self, task_id: str) -> Optional[str]:
        """Poll 2Captcha for the task result."""
        params = {
            "key": self.api_key,
            "action": "get",
            "id": task_id,
            "json": 1,
        }

        deadline = time.time() + self.timeout

        while time.time() < deadline:
            time.sleep(self.poll_interval)

            try:
                resp = requests.get(f"{API_BASE}/res.php", params=params, timeout=30)
                data = resp.json()

                if data.get("status") == 1:
                    return str(data.get("request"))
                elif data.get("request") == "CAPCHA_NOT_READY":
                    continue
                else:
                    logger.error(f"2Captcha result error: {data.get('request')}")
                    return None

            except requests.RequestException as e:
                logger.error(f"2Captcha poll error: {e}")
                continue

        logger.warning(f"2Captcha task {task_id} timed out after {self.timeout}s")
        return None

    def get_balance(self) -> Optional[float]:
        """Check 2Captcha account balance."""
        try:
            resp = requests.get(
                f"{API_BASE}/res.php",
                params={"key": self.api_key, "action": "getbalance", "json": 1},
                timeout=10,
            )
            data = resp.json()
            if data.get("status") == 1:
                return float(data.get("request", 0))
        except Exception as e:
            logger.error(f"Failed to get 2Captcha balance: {e}")
        return None
