"""Guardado y exportación de listados de videos en CSV, Markdown, TXT y JSON."""
from __future__ import annotations

import csv
import json
import logging
import os

from .utils import formatear_duracion

logger = logging.getLogger("jdownloader-mcp.youtube.export")

OUTPUT_DIR = "outputs"

CAMPOS_CSV = [
    "position", "position_str", "title", "filename", "video_id", "url",
    "published_at", "thumbnail", "duration_seconds", "views", "likes",
    "category_id", "language", "is_spanish", "status", "downloaded",
    "download_date", "local_file", "sha256", "filesize",
]


def carpeta_canal(channel_name: str) -> str:
    carpeta = os.path.join(OUTPUT_DIR, channel_name)
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _ruta_salida(nombre_archivo: str, channel_name: str) -> str:
    return os.path.join(carpeta_canal(channel_name), nombre_archivo)


def ruta_json(channel_name: str) -> str:
    return _ruta_salida("videos.json", channel_name)


def save_to_files(videos: list[dict], channel_name: str) -> dict[str, str]:
    """Guarda el listado en CSV, Markdown, TXT y JSON dentro de outputs/<channel_name>/."""
    csv_file = _ruta_salida("videos.csv", channel_name)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(videos)

    md_file = _ruta_salida("videos.md", channel_name)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# Videos del canal @{channel_name}\n\n")
        f.write(f"**Total:** {len(videos)} videos (excluye Shorts y Lives) | "
                f"**Orden:** más nuevo arriba\n\n")
        f.write("| # | Fecha | Idioma | Título | Duración | Vistas | Estado | URL |\n")
        f.write("|---|-------|--------|--------|----------|--------|--------|-----|\n")
        for v in videos:
            date = v.get("published_at", "")[:10]
            title = v.get("title", "").replace("|", "\\|")
            lang = "ES 🇪🇸" if v.get("is_spanish") else f"Otro ({v.get('language', 'en')})"
            duracion = formatear_duracion(v.get("duration_seconds", 0))
            vistas = f"{v.get('views', 0):,}".replace(",", ".")
            f.write(
                f"| {v.get('position')} | {date} | {lang} | {title} | {duracion} | "
                f"{vistas} | {v.get('status')} | [Ver]({v.get('url')}) |\n"
            )

    txt_file = _ruta_salida("urls.txt", channel_name)
    with open(txt_file, "w", encoding="utf-8") as f:
        for v in videos:
            f.write(f"{v['url']}\n")

    json_file = ruta_json(channel_name)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Archivos exportados en {carpeta_canal(channel_name)}")
    return {
        "csv": csv_file,
        "md": md_file,
        "txt": txt_file,
        "json": json_file,
    }
