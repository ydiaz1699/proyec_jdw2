"""Detección de idioma para videos de YouTube (Español vs Otro idioma)."""
from __future__ import annotations

import re
import unicodedata
from typing import TypedDict


# Palabras funcionales (stopwords) muy frecuentes en español
_SPANISH_STOPWORDS = {
    "el", "la", "de", "que", "en", "los", "del", "se", "las", "por", "un",
    "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "más",
    "pero", "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre",
    "cuando", "muy", "sin", "sobre", "ser", "tiene", "también", "tambien",
    "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante",
    "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante",
    "ellos", "esto", "mí", "mi", "antes", "algunos", "qué", "unos", "yo",
    "otro", "otras", "otra", "él", "tanto", "esa", "estos", "mucho", "quienes",
    "nada", "muchos", "cual", "poco", "ella", "estar", "estas", "algo",
    "nosotros", "mis", "tu", "tus", "te", "ti", "temporada", "capitulo",
    "capítulo", "episodio", "completo", "resumen", "pelicula", "película"
}

# Palabras funcionales en inglés frecuentes
_ENGLISH_STOPWORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
    "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
    "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
    "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "when",
    "make", "can", "like", "time", "just", "him", "know", "take", "into",
    "your", "some", "could", "them", "see", "other", "than", "then", "now",
    "look", "only", "come", "its", "over", "think", "also", "back", "after",
    "use", "how", "our", "work", "first", "well", "way", "even", "new",
    "want", "because", "any", "these", "give", "day", "most", "us",
    "full", "episode", "season", "review", "gameplay", "trailer"
}

_WORD_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


class LanguageDetectionResult(TypedDict):
    language: str       # "es", "en", u otro código ISO
    is_spanish: bool    # True si es español, False en cualquier otro caso
    method: str         # "metadata_audio", "metadata_snippet", "text_analysis", etc.
    confidence: float   # 0.0 a 1.0


def normalize_text(text: str) -> str:
    """Normaliza texto a minúsculas y elimina tildes para conteos flexibles."""
    if not text:
        return ""
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8").lower()


def detect_language_from_text(title: str, description: str = "") -> LanguageDetectionResult:
    """
    Detecta si el título y descripción corresponden a español o a otro idioma
    analizando palabras clave, caracteres únicos (ñ, ¿, ¡) y stopwords.
    """
    combined = f"{title} {description}".strip()
    if not combined:
        return {
            "language": "es",
            "is_spanish": True,
            "method": "default_fallback",
            "confidence": 0.5,
        }

    # Señales inequívocas de español
    lower_raw = combined.lower()
    if any(c in lower_raw for c in ("ñ", "¿", "¡")):
        return {
            "language": "es",
            "is_spanish": True,
            "method": "spanish_characters",
            "confidence": 0.95,
        }

    words = _WORD_RE.findall(lower_raw)
    if not words:
        return {
            "language": "es",
            "is_spanish": True,
            "method": "default_fallback",
            "confidence": 0.5,
        }

    es_count = sum(1 for w in words if w in _SPANISH_STOPWORDS)
    en_count = sum(1 for w in words if w in _ENGLISH_STOPWORDS)

    total_matches = es_count + en_count
    if total_matches == 0:
        # Si no hay matches evidentes pero hay palabras comunes en español
        return {
            "language": "es",
            "is_spanish": True,
            "method": "heuristic_neutral",
            "confidence": 0.6,
        }

    if es_count >= en_count:
        confidence = es_count / total_matches if total_matches else 0.5
        return {
            "language": "es",
            "is_spanish": True,
            "method": "text_analysis",
            "confidence": round(confidence, 2),
        }
    else:
        confidence = en_count / total_matches if total_matches else 0.5
        return {
            "language": "en",
            "is_spanish": False,
            "method": "text_analysis",
            "confidence": round(confidence, 2),
        }


def detect_video_language(
    title: str = "",
    description: str = "",
    default_audio_language: str = "",
    default_language: str = "",
) -> LanguageDetectionResult:
    """
    Determina el idioma combinando metadatos oficiales de la API de YouTube
    con análisis de texto de respaldo.
    """
    # 1. Metadatos de audio oficiales de la API
    audio_lang = (default_audio_language or "").strip().lower()
    if audio_lang:
        lang_code = audio_lang.split("-")[0].split("_")[0]
        return {
            "language": lang_code,
            "is_spanish": (lang_code == "es"),
            "method": "metadata_audio",
            "confidence": 1.0,
        }

    # 2. Metadatos generales del snippet
    snippet_lang = (default_language or "").strip().lower()
    if snippet_lang:
        lang_code = snippet_lang.split("-")[0].split("_")[0]
        return {
            "language": lang_code,
            "is_spanish": (lang_code == "es"),
            "method": "metadata_snippet",
            "confidence": 0.95,
        }

    # 3. Análisis de título y descripción
    return detect_language_from_text(title, description)
