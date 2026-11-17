"""Módulo integrado de YouTube para JDownloader MCP."""
from .filter import classify_youtube_link, filter_collector_links
from .key_router import KeyRouter, QuotaExhaustedError
from .language import detect_language_from_text, detect_video_language
from .pipeline import add_youtube_video_smart, sync_youtube_channel_to_jd

__all__ = [
    "KeyRouter",
    "QuotaExhaustedError",
    "detect_language_from_text",
    "detect_video_language",
    "classify_youtube_link",
    "filter_collector_links",
    "add_youtube_video_smart",
    "sync_youtube_channel_to_jd",
]
