"""Pipeline integrador entre YouTube y el LinkCollector de JDownloader."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .api import get_all_videos, get_channel_id, get_uploads_playlist_id
from .diff import comparar_videos, formatear_resumen_diff
from .export import ruta_json, save_to_files
from .filter import filter_collector_links
from .key_router import KeyRouter
from .language import detect_language_from_text, detect_video_language
from .utils import cargar_estado_previo, extraer_handle, extraer_video_id

logger = logging.getLogger("jdownloader-mcp.youtube.pipeline")


def _esperar_links_en_linkgrabber(
    device: Any,
    video_id: str,
    max_espera_segundos: int = 15,
    intervalo_segundos: float = 1.5,
) -> List[Dict[str, Any]]:
    """
    Sondea el LinkCollector de JDownloader hasta que el crawler haya resuelto
    los enlaces del video especificado o se agote el tiempo de espera.
    """
    inicio = time.time()
    while time.time() - inicio < max_espera_segundos:
        try:
            params = {
                "bytesTotal": True,
                "status": True,
                "availability": True,
                "url": True,
                "name": True,
                "packageUUID": True,
                "uuid": True,
            }
            todos_links = device.linkgrabber.query_links([params])
            coincidentes = [
                l for l in todos_links
                if video_id in (l.get("url") or "") or video_id in (l.get("name") or "")
            ]
            if coincidentes:
                # Dar 1 segundo adicional para asegurar que todas las variantes (video, audio, etc.) llegaron
                time.sleep(1.0)
                todos_links = device.linkgrabber.query_links([params])
                return [
                    l for l in todos_links
                    if video_id in (l.get("url") or "") or video_id in (l.get("name") or "")
                ]
        except Exception as e:
            logger.debug(f"Error consultando linkgrabber: {e}")

        time.sleep(intervalo_segundos)

    return []


def add_youtube_video_smart(
    device: Any,
    url: str,
    package_name: str = "",
    auto_start: bool = False,
    is_spanish: Optional[bool] = None,
    max_wait_seconds: int = 15,
) -> Dict[str, Any]:
    """
    Agrega un video individual de YouTube a JDownloader, espera a que LinkCollector
    resuelva las variantes, determina el idioma y filtra los archivos:

    - Conserva Video, Miniatura, Descripción y Subtítulos (.srt/.vtt para la base de conocimiento).
    - Elimina Audio suelto (.m4a/.aac) y otros archivos redundantes.
    """
    vid = extraer_video_id(url)
    clean_url = f"https://www.youtube.com/watch?v={vid}"

    # Si no se especificó is_spanish, intentamos detectarlo
    metodo_deteccion = "explicit"
    if is_spanish is None:
        # 1. Intentar con YouTube API si hay claves en el entorno
        try:
            router = KeyRouter.from_env()
            cliente = router.get_client()
            res = cliente.videos().list(part="snippet", id=vid).execute()
            items = res.get("items", [])
            if items:
                snippet = items[0]["snippet"]
                lang_res = detect_video_language(
                    title=snippet.get("title", ""),
                    default_audio_language=snippet.get("defaultAudioLanguage", ""),
                    default_language=snippet.get("defaultLanguage", ""),
                )
                is_spanish = lang_res["is_spanish"]
                metodo_deteccion = f"youtube_api_{lang_res['method']}"
                if not package_name:
                    from .utils import sanitize_filename
                    package_name = sanitize_filename(snippet.get("title", ""))
        except Exception:
            pass

    # 2. Agregar el link al LinkCollector de JDownloader
    add_params: Dict[str, Any] = {
        "autostart": False,
        "links": clean_url,
    }
    if package_name:
        add_params["packageName"] = package_name

    logger.info(f"Añadiendo {clean_url} a LinkCollector...")
    device.linkgrabber.add_links([add_params])

    # 3. Esperar que JDownloader procese y extraiga las variantes
    logger.info(f"Esperando que JDownloader resuelva las variantes de {vid}...")
    links = _esperar_links_en_linkgrabber(device, vid, max_espera_segundos=max_wait_seconds)

    if not links:
        return {
            "status": "warning",
            "message": f"Link agregado pero no se resolvieron variantes a tiempo para {clean_url}.",
            "video_id": vid,
            "url": clean_url,
        }

    # 4. Si el idioma aún no se definió, detectarlo analizando el nombre de los links resueltos
    if is_spanish is None:
        primer_nombre = links[0].get("name", "")
        lang_res = detect_language_from_text(primer_nombre)
        is_spanish = lang_res["is_spanish"]
        metodo_deteccion = f"link_name_{lang_res['method']}"

    # 5. Filtrar variantes según la regla de idioma
    filtro_resultado = filter_collector_links(device, links, is_spanish=is_spanish)

    # 6. Autostart opcional si fue solicitado
    if auto_start:
        try:
            pkg_uuids = list({l.get("packageUUID") for l in links if l.get("packageUUID")})
            if pkg_uuids:
                device.linkgrabber.move_to_download([], pkg_uuids)
        except Exception as e:
            logger.warning(f"No se pudo mover a descargas automáticamente: {e}")

    return {
        "status": "success",
        "video_id": vid,
        "url": clean_url,
        "package_name": package_name,
        "is_spanish": is_spanish,
        "idioma_detectado": "Español" if is_spanish else "Otro idioma",
        "metodo_deteccion": metodo_deteccion,
        "total_variantes_detectadas": filtro_resultado["total_initial"],
        "archivos_conservados": [item["name"] for item in filtro_resultado["kept"]],
        "archivos_eliminados": [item["name"] for item in filtro_resultado["removed"]],
    }


def sync_youtube_channel_to_jd(
    device: Any,
    channel_handle: str,
    max_videos: int = 0,
    auto_start: bool = False,
    pause_seconds: float = 2.0,
) -> Dict[str, Any]:
    """
    Sincroniza un canal de YouTube:
    1. Extrae listado actualizado de videos usando KeyRouter.
    2. Compara con la corrida anterior (diff).
    3. Para videos pendientes, los envía a JDownloader en su propio paquete y filtra
       sus variantes según el idioma detectado en cada uno.
    4. Guarda los resultados en outputs/<canal>/.
    """
    handle = extraer_handle(channel_handle)
    router = KeyRouter.from_env()

    logger.info(f"Buscando canal @{handle}...")
    channel_id = get_channel_id(None, handle, router=router)
    playlist_id = get_uploads_playlist_id(None, channel_id, router=router)

    archivo_json = ruta_json(handle)
    estado_previo = cargar_estado_previo(archivo_json)
    videos_anteriores = []
    if estado_previo:
        try:
            import json
            with open(archivo_json, "r", encoding="utf-8") as f:
                videos_anteriores = json.load(f)
        except Exception:
            pass

    videos = get_all_videos(None, playlist_id, estado_previo=estado_previo, router=router)
    diff = comparar_videos(videos, videos_anteriores)
    save_to_files(videos, handle)

    pendientes = [v for v in videos if v.get("status") == "pending"]
    if max_videos > 0:
        pendientes = pendientes[:max_videos]

    enviados_report = []
    for i, v in enumerate(pendientes, start=1):
        logger.info(f"Procesando [{i}/{len(pendientes)}]: {v['title']} (Idioma: {'ES' if v.get('is_spanish') else 'Otro'})")
        res = add_youtube_video_smart(
            device=device,
            url=v["url"],
            package_name=v.get("filename", ""),
            auto_start=auto_start,
            is_spanish=v.get("is_spanish"),
        )
        enviados_report.append(res)
        if i < len(pendientes):
            time.sleep(pause_seconds)

    return {
        "channel": handle,
        "total_videos_canal": len(videos),
        "resumen_diff": formatear_resumen_diff(diff),
        "videos_procesados_jd": len(enviados_report),
        "detalle": enviados_report,
    }
