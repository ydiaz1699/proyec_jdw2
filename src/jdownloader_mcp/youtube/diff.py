"""Comparación diferencial entre corridas de un canal de YouTube."""
from __future__ import annotations

from typing import TypedDict


class ResultadoDiff(TypedDict):
    nuevos: list[dict]
    eliminados: list[dict]
    total_anterior: int
    total_actual: int


def comparar_videos(videos_actuales: list[dict], videos_anteriores: list[dict]) -> ResultadoDiff:
    ids_actuales = {v["video_id"] for v in videos_actuales}
    ids_anteriores = {v["video_id"] for v in videos_anteriores}

    ids_nuevos = ids_actuales - ids_anteriores
    ids_eliminados = ids_anteriores - ids_actuales

    nuevos = [v for v in videos_actuales if v["video_id"] in ids_nuevos]
    eliminados = [v for v in videos_anteriores if v["video_id"] in ids_eliminados]

    return {
        "nuevos": nuevos,
        "eliminados": eliminados,
        "total_anterior": len(videos_anteriores),
        "total_actual": len(videos_actuales),
    }


def formatear_resumen_diff(diff: ResultadoDiff) -> str:
    lineas = []
    if diff["total_anterior"] == 0:
        return "ℹ️ No había datos previos para comparar."

    if diff["nuevos"]:
        lineas.append(f"🆕 {len(diff['nuevos'])} video(s) nuevo(s):")
        for v in diff["nuevos"]:
            lineas.append(f"   + [{v['published_at'][:10]}] {v['title']}")
    else:
        lineas.append("🆕 No hay videos nuevos desde la última corrida.")

    if diff["eliminados"]:
        lineas.append(f"🗑️ {len(diff['eliminados'])} video(s) ya no están disponibles:")
        for v in diff["eliminados"]:
            lineas.append(f"   - {v['title']}")

    return "\n".join(lineas)
