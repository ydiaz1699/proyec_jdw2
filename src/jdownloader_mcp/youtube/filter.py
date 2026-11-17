"""Filtrado de variantes de YouTube en el LinkCollector de JDownloader según el idioma."""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger("jdownloader-mcp.youtube.filter")


def classify_youtube_link(name: str, url: str = "") -> str:
    """
    Clasifica un ítem de YouTube generado en el LinkCollector.
    Devuelve: 'video', 'audio', 'thumbnail', 'description', 'subtitle', o 'other'.
    """
    n = name.lower()
    ext = os.path.splitext(n)[1].lower()

    # Subtítulos
    if ext in (".srt", ".vtt") or "_asr" in n or "subtítulo" in n or "subtitle" in n:
        return "subtitle"

    # Descripción / info
    if ext == ".txt" or "descripción" in n or "description" in n:
        return "description"

    # Miniatura / portada
    if ext in (".jpg", ".jpeg", ".png", ".webp") or any(tag in n for tag in ("(bq)", "(hq)", "(mq)", "(sd)", "(maxresdefault)", "miniatura", "thumbnail")):
        return "thumbnail"

    # Audio suelto
    if ext in (".m4a", ".aac", ".ogg", ".mp3", ".opus") or ("kbit" in n and ext not in (".mp4", ".mkv", ".webm")):
        return "audio"

    # Video
    if ext in (".mp4", ".webm", ".mkv") or any(res in n for res in ("1080p", "720p", "480p", "360p", "2160p", "4k", "h264", "vp9", "av1")):
        return "video"

    return "other"


def filter_collector_links(
    device: Any,
    links: List[Dict[str, Any]],
    is_spanish: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Aplica las reglas de filtrado sobre una lista de enlaces del LinkCollector:

    Si es español:
      - Conservar: video, thumbnail, description
      - Eliminar: audio, subtitle, other

    Si es otro idioma:
      - Conservar: video, thumbnail, subtitle, description
      - Eliminar: audio, other

    Retorna un reporte con los links conservados, eliminados y sus categorías.
    """
    kept: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    ids_to_remove: List[str | int] = []

    for l in links:
        name = l.get("name", "")
        uuid = l.get("uuid")
        category = classify_youtube_link(name, l.get("url", ""))

        should_keep = False
        if category in ("video", "thumbnail", "description", "subtitle"):
            # Se conservan video, miniatura, descripción y subtítulos SIEMPRE
            # Los subtítulos (.srt/.vtt) son la materia prima esencial para el sistema de memoria
            should_keep = True
        elif category == "audio":
            # El audio suelto se descarta siempre porque el video ya incluye su pista de audio
            should_keep = False
        else:
            should_keep = False

        item_info = {
            "uuid": uuid,
            "name": name,
            "category": category,
            "packageUUID": l.get("packageUUID"),
        }

        if should_keep:
            kept.append(item_info)
        else:
            removed.append(item_info)
            if uuid is not None:
                ids_to_remove.append(uuid)

    if ids_to_remove and not dry_run:
        try:
            device.linkgrabber.remove_links(ids_to_remove, [])
            logger.info(f"🗑️ Eliminados {len(ids_to_remove)} sub-ítems no deseados del LinkCollector.")
        except Exception as e:
            logger.error(f"Error eliminando links en LinkCollector: {e}")

    return {
        "is_spanish": is_spanish,
        "total_initial": len(links),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "kept": kept,
        "removed": removed,
    }
