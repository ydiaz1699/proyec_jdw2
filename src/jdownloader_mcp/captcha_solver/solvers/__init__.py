"""Individual captcha solvers."""

from .ocr_solver import OCRSolver
from .ml_solver import MLSolver
from .nopecha_solver import NopeCHASolver
from .twocaptcha_solver import TwoCaptchaSolver
from .darknet_solver import DarkNetSolver

__all__ = [
    "OCRSolver",
    "MLSolver",
    "NopeCHASolver",
    "TwoCaptchaSolver",
    "DarkNetSolver",
]
