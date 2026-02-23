"""Motor de filtrado y búsqueda textual sobre el feed de formaciones."""

from __future__ import annotations

import logging
from datetime import datetime

from .text_utils import fuzzy_match

logger = logging.getLogger(__name__)


def filter_feed(
    items: list[dict],
    query: str = "",
    country: str | None = None,
    language: str | None = None,
    tipo: str | None = None,
    audiencia: str | None = None,
    area_solucion: str | None = None,
    provider: str | None = None,
    desde_fecha: str | None = None,
    hasta_fecha: str | None = None,
) -> list[dict]:
    """Filtra el feed con múltiples criterios combinables.

    Args:
        items: Lista completa del feed.
        query: Texto a buscar en títulos y tecnologías (fuzzy, sin tildes).
        country: Código ISO de país (ej: "es", "de").
        language: Idioma (ej: "Spanish", "English").
        tipo: Tipo de contenido: webinar, video, audio, download, link, event, track, podcast.
        audiencia: Público: Sales, Technical.
        area_solucion: Área: ai-platform, ai-business-process, ai-workforce, cross-solution, security.
        provider: Proveedor: microsoft, levelup, cloud champion.
        desde_fecha: Fecha inicio (YYYY-MM-DD).
        hasta_fecha: Fecha fin (YYYY-MM-DD).

    Returns:
        Lista filtrada, ordenada por fecha descendente.
    """
    results = items

    if country:
        results = [
            i for i in results
            if country.lower() in [c.lower() for c in i.get("countries", [])]
        ]

    if language:
        results = [
            i for i in results
            if language.lower() in [lang.lower() for lang in i.get("language", [])]
        ]

    if tipo:
        results = [
            i for i in results
            if i.get("type", "").lower() == tipo.lower()
        ]

    if audiencia:
        results = [
            i for i in results
            if audiencia.lower() in [a.lower() for a in i.get("audience", [])]
        ]

    if area_solucion:
        results = [
            i for i in results
            if area_solucion.lower() in [a.lower() for a in i.get("solution_area", [])]
        ]

    if provider:
        results = [
            i for i in results
            if i.get("provider", "").lower() == provider.lower()
        ]

    if desde_fecha:
        desde = datetime.strptime(desde_fecha, "%Y-%m-%d")
        results = [
            i for i in results
            if _parse_date(i) is not None and _parse_date(i) >= desde  # type: ignore[operator]
        ]

    if hasta_fecha:
        hasta = datetime.strptime(hasta_fecha, "%Y-%m-%d")
        results = [
            i for i in results
            if _parse_date(i) is not None and _parse_date(i) <= hasta  # type: ignore[operator]
        ]

    if query:
        results = [
            i for i in results
            if fuzzy_match(query, i.get("title", ""))
            or any(fuzzy_match(query, t) for t in i.get("technologies", []))
        ]

    # Ordenar por fecha descendente (items sin fecha al final)
    results.sort(key=lambda i: i.get("Date") or "", reverse=True)

    logger.debug("filter_feed: %d → %d items", len(items), len(results))
    return results


def _parse_date(item: dict) -> datetime | None:
    """Parsea el campo Date del feed. Devuelve None si es nulo, vacío o inválido."""
    raw = item.get("Date")
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y%m%d")
    except (ValueError, TypeError):
        return None
