"""
JDownloader Captcha Auto-Solver
===============================
Self-contained module for automatically solving captchas detected by JDownloader.

Supports:
- Text/image captchas via OCR (Tesseract, EasyOCR) and custom ML models
- reCAPTCHA v2/v3, hCaptcha, Turnstile via NopeCHA API (self-hosted client)
- reCAPTCHA v2/v3, hCaptcha, Turnstile via 2Captcha API
- Geometric/YOLO captchas via cracker0dks/CaptchaSolver integration

Architecture:
    CaptchaRouter -> detects type -> routes to appropriate Solver
    AutoSolverDaemon -> polls JDownloader -> auto-solves pending captchas
"""

__version__ = "1.1.0"

from .base import BaseSolver, CaptchaChallenge, CaptchaSolution, CaptchaType
from .router import CaptchaRouter
from .daemon import AutoSolverDaemon
