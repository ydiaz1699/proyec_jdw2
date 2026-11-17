"""Llamadas a la API de YouTube Data v3, con retries, cuota, filtrado y detección de idioma."""
from __future__ import annotations

import json
import logging
import random
import time
from typing import Any, Callable

from googleapiclient.errors import HttpError
from tqdm import tqdm

from .key_router import KeyRouter, QuotaExhaustedError
from .language import detect_video_language
from .quota import registrar_uso
from .utils import parse_duration_iso8601, sanitize_filename

logger = logging.getLogger("jdownloader-mcp.youtube.api")

MAX_RESULTS = 50
RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}
QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.5

COSTO_OPERACION = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
}


def _razon_http_error(e: HttpError) -> str:
    try:
        return json.loads(e.content).get("error", {}).get("errors", [{}])[0].get("reason", "")
    except Exception:
        return ""


def with_retries(
    build_request: Callable[[Any], Any],
    operacion: str = "unknown",
    *,
    router: KeyRouter | None = None,
    youtube: Any = None,
) -> dict:
    last_error: HttpError | None = None

    for intento in range(1, MAX_RETRIES + 1):
        if router is not None:
            slot = router.get_slot()
            cliente = slot.get_client()
            label = slot.label
        else:
            cliente = youtube
            label = None

        try:
            resultado = build_request(cliente).execute()
            costo = COSTO_OPERACION.get(operacion, 1)
            registrar_uso(operacion)
            if router is not None and label:
                router.report_cost(costo, label=label)
            return resultado
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            razon = _razon_http_error(e)
            last_error = e

            if status == 403 and razon in QUOTA_REASONS and router is not None and label:
                logger.warning(f"  🚨 Cuota agotada en la API key '{label}'. Rotando...")
                router.mark_exhausted(label)
                continue

            if status not in RETRYABLE_STATUS_CODES or intento == MAX_RETRIES:
                raise

            espera = BASE_BACKOFF_SECONDS * (2 ** (intento - 1)) + random.uniform(0, 0.5)
            logger.warning(
                f"  ⚠️ Error {status} (intento {intento}/{MAX_RETRIES}), reintentando en {espera:.1f}s..."
            )
            time.sleep(espera)

    if last_error is not None:
        raise last_error
    raise RuntimeError("with_retries terminó sin resultado ni excepción.")


def get_channel_id(youtube: Any, channel_handle: str, router: KeyRouter | None = None) -> str:
    response = with_retries(
        lambda yt: yt.channels().list(part="id", forHandle=channel_handle),
        "channels.list",
        router=router,
        youtube=youtube,
    )
    items = response.get("items", [])
    if not items:
        raise ValueError(
            f"No se encontró ningún canal con el handle '@{channel_handle}'."
        )
    return items[0]["id"]


def get_uploads_playlist_id(
    youtube: Any,
    channel_id: str,
    router: KeyRouter | None = None,
    only_videos_tab: bool = True,
) -> str:
    """
    Obtiene el ID de la playlist del canal.
    Si only_videos_tab=True (por defecto), usa la playlist nativa de la pestaña 'Videos'
    (prefijo 'UULF'), excluyendo automáticamente Shorts, En Vivo, Podcasts y Cursos.
    """
    if only_videos_tab and channel_id.startswith("UC"):
        uulf_id = f"UULF{channel_id[2:]}"
        try:
            with_retries(
                lambda yt: yt.playlistItems().list(part="id", playlistId=uulf_id, maxResults=1),
                "playlistItems.list",
                router=router,
                youtube=youtube,
            )
            logger.info(f"🎯 Usando playlist nativa de la pestaña 'Videos' (excluye Shorts/Lives/Podcasts): {uulf_id}")
            return uulf_id
        except Exception as e:
            logger.debug(f"Playlist UULF no disponible ({e}), cayendo a uploads general.")

    response = with_retries(
        lambda yt: yt.channels().list(part="contentDetails", id=channel_id),
        "channels.list",
        router=router,
        youtube=youtube,
    )
    items = response.get("items", [])
    if not items:
        raise ValueError(f"No se encontró el canal con ID {channel_id}.")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_playlist_items(youtube: Any, playlist_id: str, router: KeyRouter | None = None) -> list[dict]:
    items: list[dict] = []
    next_page_token: str | None = None

    while True:
        response = with_retries(
            lambda yt, tok=next_page_token: yt.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=MAX_RESULTS,
                pageToken=tok,
            ),
            "playlistItems.list",
            router=router,
            youtube=youtube,
        )

        for item in response.get("items", []):
            snippet = item["snippet"]
            items.append({
                "title": snippet["title"],
                "video_id": snippet["resourceId"]["videoId"],
                "url": f"https://youtube.com/watch?v={snippet['resourceId']['videoId']}",
                "published_at": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", "N/A"),
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return items


def filtrar_solo_videos(youtube: Any, items: list[dict], router: KeyRouter | None = None) -> list[dict]:
    videos_filtrados: list[dict] = []
    ids = [v["video_id"] for v in items]
    por_id = {v["video_id"]: v for v in items}

    lotes = [ids[i:i + 50] for i in range(0, len(ids), 50)]

    for lote in lotes:
        response = with_retries(
            lambda yt, batch=lote: yt.videos().list(
                part="contentDetails,snippet,statistics,liveStreamingDetails",
                id=",".join(batch),
            ),
            "videos.list",
            router=router,
            youtube=youtube,
        )

        for item in response.get("items", []):
            vid = item["id"]
            duracion_iso = item["contentDetails"]["duration"]
            live_status = item["snippet"].get("liveBroadcastContent", "none")
            has_live_details = "liveStreamingDetails" in item
            segundos = parse_duration_iso8601(duracion_iso)

            # Excluir Shorts (hasta 180s o etiqueta #shorts)
            es_short = segundos <= 60 or (segundos <= 180 and "#shorts" in (item["snippet"].get("title", "") + item["snippet"].get("description", "")).lower())
            # Excluir cualquier transmisión en vivo (activa, próxima o pasada/grabada)
            es_live = has_live_details or live_status in ("live", "upcoming")
            if es_short or es_live:
                continue

            video = por_id[vid]
            estadisticas = item.get("statistics", {})
            snippet = item.get("snippet", {})

            video["duration_seconds"] = segundos
            video["views"] = int(estadisticas.get("viewCount", 0))
            video["likes"] = int(estadisticas.get("likeCount", 0))
            video["category_id"] = snippet.get("categoryId")

            # Detección de idioma integrada
            default_audio = snippet.get("defaultAudioLanguage", "")
            default_lang = snippet.get("defaultLanguage", "")
            lang_info = detect_video_language(
                title=video.get("title", ""),
                default_audio_language=default_audio,
                default_language=default_lang,
            )
            video["language"] = lang_info["language"]
            video["is_spanish"] = lang_info["is_spanish"]
            video["language_method"] = lang_info["method"]

            videos_filtrados.append(video)

    return videos_filtrados


def get_all_videos(
    youtube: Any,
    playlist_id: str,
    estado_previo: dict[str, dict] | None = None,
    router: KeyRouter | None = None,
) -> list[dict]:
    items = get_playlist_items(youtube, playlist_id, router=router)
    videos = filtrar_solo_videos(youtube, items, router=router)

    # Orden cronológico (antiguo -> nuevo) para numeración
    videos.sort(key=lambda v: v["published_at"])
    total_videos = len(videos)

    if total_videos < 100:
        padding = 2
    elif total_videos < 1000:
        padding = 3
    else:
        padding = 4

    for pos, v in enumerate(videos, start=1):
        v["position"] = pos
        v["position_str"] = f"{pos:0{padding}d}"
        sanitized = sanitize_filename(v["title"])
        v["filename"] = f"{v['position_str']}.- {sanitized}.mp4"

        # Preservar o inicializar estado
        vid = v["video_id"]
        if estado_previo and vid in estado_previo:
            prev = estado_previo[vid]
            v["status"] = prev.get("status", "pending")
            v["downloaded"] = prev.get("downloaded", False)
            v["download_date"] = prev.get("download_date")
            v["local_file"] = prev.get("local_file")
            v["sha256"] = prev.get("sha256")
            v["filesize"] = prev.get("filesize")
        else:
            v["status"] = "pending"
            v["downloaded"] = False
            v["download_date"] = None
            v["local_file"] = None
            v["sha256"] = None
            v["filesize"] = None

    # Devolver con el más nuevo arriba
    videos.reverse()
    return videos
