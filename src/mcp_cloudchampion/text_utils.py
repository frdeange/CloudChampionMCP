"""Utilidades de normalización de texto para búsqueda fuzzy multiidioma."""

from __future__ import annotations

import unicodedata


def normalize(text: str) -> str:
    """Quita tildes/diacríticos, pasa a minúsculas, elimina espacios extra."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()


def fuzzy_match(query: str, text: str) -> bool:
    """Comprueba si todas las palabras del query aparecen en el texto normalizado."""
    if not query or not text:
        return False
    query_words = normalize(query).split()
    normalized_text = normalize(text)
    return all(word in normalized_text for word in query_words)
