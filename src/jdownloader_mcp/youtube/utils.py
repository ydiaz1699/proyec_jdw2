"""Funciones auxiliares para el procesamiento de URLs y metadatos de YouTube."""
from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger("jdownloader-mcp.youtube.utils")


def sanitize_filename(name: str) -> str:
    """Elimina caracteres no válidos para nombres de archivo en Windows y Linux."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.replace("\n", " ").strip()
    return name


def parse_duration_iso8601(duracion: str | None) -> int:
    """Convierte duración ISO 8601 (ej. 'PT1M30S') a segundos totales."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duracion or "")
    if not match:
        return 0
    horas, minutos, segundos = match.groups()
    horas_i = int(horas) if horas else 0
    minutos_i = int(minutos) if minutos else 0
    segundos_i = int(segundos) if segundos else 0
    return horas_i * 3600 + minutos_i * 60 + segundos_i


def formatear_duracion(segundos: int) -> str:
    """Convierte segundos a formato legible HH:MM:SS o MM:SS."""
    horas, resto = divmod(segundos, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"
    return f"{minutos:02d}:{segs:02d}"


def extraer_handle(texto: str) -> str:
    """Extrae el handle de un canal a partir de texto o URL."""
    texto = texto.strip()
    if "youtube.com/@" in texto:
        texto = texto.split("youtube.com/@")[1].split("/")[0].split("?")[0]
    elif "youtube.com/" in texto:
        texto = texto.rstrip("/").split("/")[-1].split("?")[0]
    return texto.lstrip("@")


def extraer_video_id(url_o_id: str) -> str:
    """Extrae el ID de 11 caracteres de un video de YouTube desde diversas formas de URL."""
    url = url_o_id.strip()
    if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url

    match = re.search(r"(?:v=|\/|youtu\.be\/)([A-Za-z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return url


def cargar_estado_previo(archivo_json: str) -> dict[str, dict]:
    """Carga estado previo de un archivo JSON de videos si existe."""
    if not os.path.exists(archivo_json):
        return {}
    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            videos = json.load(f)
        return {
            v["video_id"]: {
                "status": v.get("status", "pending"),
                "downloaded": v.get("downloaded", False),
                "download_date": v.get("download_date"),
                "local_file": v.get("local_file"),
                "sha256": v.get("sha256"),
                "filesize": v.get("filesize"),
                "language": v.get("language"),
                "is_spanish": v.get("is_spanish"),
            }
            for v in videos
            if "video_id" in v
        }
    except Exception as e:
        logger.warning(f"No se pudo cargar estado previo de {archivo_json}: {e}")
        return {}
