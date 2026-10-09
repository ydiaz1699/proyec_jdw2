"""Individual captcha solvers.

Importación perezosa: los solvers que dependen de paquetes pesados u opcionales
(torch para MLSolver/DarkNetSolver, tesseract/easyocr para OCRSolver) NO se
importan al cargar el paquete. Así, importar ``jdownloader_mcp`` o el paquete
``captcha_solver`` nunca arrastra torch ni revienta si no está instalado.

Los solvers de API externa (NopeCHA, 2Captcha) sólo requieren ``requests`` y son
los únicos que el servidor registra por defecto (según sus API keys).

Acceder a ``solvers.MLSolver`` importa su módulo en ese momento; si falta la
dependencia, el ``ImportError`` se lanza ahí, de forma explícita.
"""

from importlib import import_module

__all__ = [
    "OCRSolver",
    "MLSolver",
    "NopeCHASolver",
    "TwoCaptchaSolver",
    "DarkNetSolver",
]

_LAZY = {
    "OCRSolver": ".ocr_solver",
    "MLSolver": ".ml_solver",
    "NopeCHASolver": ".nopecha_solver",
    "TwoCaptchaSolver": ".twocaptcha_solver",
    "DarkNetSolver": ".darknet_solver",
}


def __getattr__(name):
    """PEP 562 lazy attribute access for solver classes."""
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
