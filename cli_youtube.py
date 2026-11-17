#!/usr/bin/env python3
"""CLI para YouTube + JDownloader (Extracción, Detección de Idioma y Filtrado).

Uso:
    python cli_youtube.py add "https://www.youtube.com/watch?v=..."
    python cli_youtube.py sync --handle FeZaThreatBlock --send-jd
    python cli_youtube.py filter --lang es
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Permitir importar desde src/
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import myjdapi


def get_jd_device():
    email = os.getenv("JD_EMAIL")
    pwd = os.getenv("JD_PASSWORD")
    device_name = os.getenv("JD_DEVICE_NAME")

    if not (email and pwd):
        # Intentar cargar desde mcp_config.json
        cfg_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
        if cfg_path.is_file():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                env = cfg.get("mcpServers", {}).get("jdownloader", {}).get("env", {})
                email = email or env.get("JD_EMAIL")
                pwd = pwd or env.get("JD_PASSWORD")
                device_name = device_name or env.get("JD_DEVICE_NAME")
            except Exception:
                pass

    if not (email and pwd):
        print("❌ Error: Faltan credenciales JD_EMAIL y JD_PASSWORD.")
        sys.exit(1)

    jd = myjdapi.Myjdapi()
    jd.set_app_key("cli_youtube_jdownloader")
    print("🔐 Conectando a My.JDownloader...")
    jd.connect(email, pwd)
    jd.update_devices()
    devices = jd.list_devices()
    if not devices:
        print("❌ No se encontraron dispositivos JDownloader online.")
        sys.exit(1)

    if device_name:
        device = jd.get_device(device_name)
        if device is None:
            device = jd.get_device(devices[0]["name"])
    else:
        device = jd.get_device(devices[0]["name"])

    print(f"✅ Dispositivo conectado: {device.name}")
    return jd, device


def cmd_add(args):
    from jdownloader_mcp.youtube.pipeline import add_youtube_video_smart
    jd, device = get_jd_device()
    try:
        is_spanish = None
        if args.lang:
            is_spanish = (args.lang.lower() in ("es", "spanish", "español"))

        print(f"📥 Agregando video de forma inteligente: {args.url}")
        res = add_youtube_video_smart(
            device=device,
            url=args.url,
            package_name=args.package_name or "",
            auto_start=args.autostart,
            is_spanish=is_spanish,
        )
        print("\n📊 Resultado:")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    finally:
        jd.disconnect()


def cmd_filter(args):
    from jdownloader_mcp.youtube.filter import filter_collector_links
    jd, device = get_jd_device()
    try:
        is_spanish = (args.lang.lower() in ("es", "spanish", "español"))
        print("🧹 Filtrando LinkCollector: conservando Video + Miniatura + Descripción + Subtítulos (.srt); eliminando Audio suelto.")
        params = {
            "bytesTotal": True,
            "status": True,
            "availability": True,
            "url": True,
            "name": True,
            "packageUUID": True,
            "uuid": True,
        }
        links = device.linkgrabber.query_links([params])
        res = filter_collector_links(device, links, is_spanish=is_spanish, dry_run=args.dry_run)
        print("\n📊 Resultado del filtrado:")
        print(f"   Total inicial: {res['total_initial']}")
        print(f"   Conservados: {res['kept_count']}")
        print(f"   Eliminados:  {res['removed_count']}")
    finally:
        jd.disconnect()


def cmd_sync(args):
    from jdownloader_mcp.youtube.pipeline import sync_youtube_channel_to_jd
    jd, device = get_jd_device()
    try:
        print(f"🔄 Sincronizando canal @{args.handle} con JDownloader...")
        res = sync_youtube_channel_to_jd(
            device=device,
            channel_handle=args.handle,
            max_videos=args.max_videos,
            auto_start=args.autostart,
        )
        print("\n📊 Resultado de la sincronización:")
        print(f"   Total videos canal: {res['total_videos_canal']}")
        print(f"   Videos enviados a JD: {res['videos_procesados_jd']}")
        print(f"   Resumen diff:\n{res['resumen_diff']}")
    finally:
        jd.disconnect()


def main():
    parser = argparse.ArgumentParser(description="YouTube + JDownloader CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="Agregar video individual con filtrado inteligente")
    p_add.add_argument("url", help="URL del video de YouTube")
    p_add.add_argument("--package-name", default="", help="Nombre personalizado para el paquete")
    p_add.add_argument("--lang", default="", help="Forzar idioma: 'es' u 'otro'")
    p_add.add_argument("--autostart", action="store_true", help="Iniciar descarga inmediatamente")
    p_add.set_defaults(func=cmd_add)

    # filter
    p_filter = subparsers.add_parser("filter", help="Filtrar variantes actuales del LinkCollector")
    p_filter.add_argument("--lang", default="es", help="Idioma: 'es' u 'otro' (defecto: es)")
    p_filter.add_argument("--dry-run", action="store_true", help="Simular sin borrar nada")
    p_filter.set_defaults(func=cmd_filter)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sincronizar canal completo hacia JDownloader")
    p_sync.add_argument("--handle", required=True, help="Handle del canal (ej. FeZaThreatBlock)")
    p_sync.add_argument("--max-videos", type=int, default=0, help="Límite de videos a procesar (0 = todos)")
    p_sync.add_argument("--autostart", action="store_true", help="Iniciar descarga inmediatamente")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
