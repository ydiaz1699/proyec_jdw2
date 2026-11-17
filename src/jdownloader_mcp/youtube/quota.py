"""Tracking aproximado de la cuota diaria de la API de YouTube Data v3."""
from __future__ import annotations

import json
import logging
import os
from datetime import date

logger = logging.getLogger("jdownloader-mcp.youtube.quota")

QUOTA_FILE = os.path.join("outputs", ".quota_cache.json")
LIMITE_DIARIO_DEFAULT = 10_000

COSTOS = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "search.list": 100,
}


def _leer_cache() -> dict:
    if not os.path.exists(QUOTA_FILE):
        return {"fecha": str(date.today()), "consumido": 0}

    try:
        with open(QUOTA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"fecha": str(date.today()), "consumido": 0}

    if data.get("fecha") != str(date.today()):
        return {"fecha": str(date.today()), "consumido": 0}

    return data


def _guardar_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def registrar_uso(operacion: str, limite_diario: int = LIMITE_DIARIO_DEFAULT) -> int:
    costo = COSTOS.get(operacion, 1)
    data = _leer_cache()
    data["consumido"] = data.get("consumido", 0) + costo
    _guardar_cache(data)

    consumido = data["consumido"]
    restante = limite_diario - consumido

    if consumido >= limite_diario:
        logger.warning(
            f"🚨 CUOTA AGOTADA (estimada): consumiste {consumido}/{limite_diario} unidades hoy."
        )
    elif restante <= 1_000:
        logger.warning(
            f"⚠️  Cuota baja: consumidas {consumido}/{limite_diario} unidades "
            f"({restante} restantes estimadas)."
        )

    return consumido


def estado_cuota(limite_diario: int = LIMITE_DIARIO_DEFAULT) -> dict:
    data = _leer_cache()
    consumido = data.get("consumido", 0)
    return {
        "fecha": data.get("fecha", str(date.today())),
        "consumido": consumido,
        "limite": limite_diario,
        "restante": max(0, limite_diario - consumido),
        "porcentaje_usado": round((consumido / limite_diario) * 100, 1),
    }
