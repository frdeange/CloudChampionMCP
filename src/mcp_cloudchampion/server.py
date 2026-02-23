"""Servidor MCP para el catálogo de formación de Cloud Champion."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from .config import settings, setup_logging
from .feed_client import feed_client
from .filters import filter_feed
from .text_utils import fuzzy_match

setup_logging()
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="CloudChampion",
    instructions=(
        "Servidor MCP para consultar el catálogo de formación de Cloud Champion "
        "(cloudchampion.es/.co/.de/.it/etc.). Permite buscar formaciones, filtrar "
        "por país, idioma, tipo, audiencia, área de solución, proveedor y fechas. "
        "El catálogo incluye webinars, vídeos, learning paths, podcasts y otros "
        "recursos de Microsoft para partners."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: buscar_formacion
# ---------------------------------------------------------------------------
@mcp.tool()
async def buscar_formacion(
    query: str = "",
    country: str | None = None,
    language: str | None = None,
    tipo: str | None = None,
    audiencia: str | None = None,
    area_solucion: str | None = None,
    provider: str | None = None,
    desde_fecha: str | None = None,
    hasta_fecha: str | None = None,
    max_resultados: int = 20,
) -> list[dict]:
    """Busca formaciones en el catálogo de Cloud Champion.

    Args:
        query: Texto a buscar en títulos y tecnologías (búsqueda fuzzy, sin tildes).
        country: Código ISO de país (ej: "es", "de", "it", "nl", "se", "dk", "at", "ch", "be", "ie", "fi", "no", "pt").
        language: Idioma (ej: "Spanish", "English", "German", "Italian", "Finnish").
        tipo: Tipo de contenido: webinar, video, audio, download, link, event, track, podcast.
        audiencia: Público objetivo: Sales, Technical.
        area_solucion: Área de solución: ai-platform, ai-business-process, ai-workforce, cross-solution, security.
        provider: Proveedor: microsoft, levelup, cloud champion.
        desde_fecha: Fecha inicio filtro (YYYY-MM-DD).
        hasta_fecha: Fecha fin filtro (YYYY-MM-DD).
        max_resultados: Número máximo de resultados (default 20).
    """
    logger.info(
        "buscar_formacion: query=%r country=%s language=%s tipo=%s",
        query, country, language, tipo,
    )
    feed = await feed_client.get_feed()
    results = filter_feed(
        feed,
        query=query,
        country=country,
        language=language,
        tipo=tipo,
        audiencia=audiencia,
        area_solucion=area_solucion,
        provider=provider,
        desde_fecha=desde_fecha,
        hasta_fecha=hasta_fecha,
    )
    return _format_results(results[:max_resultados])


# ---------------------------------------------------------------------------
# Tool 2: listar_proximas_formaciones
# ---------------------------------------------------------------------------
@mcp.tool()
async def listar_proximas_formaciones(
    dias: int = 30,
    country: str | None = None,
    language: str | None = None,
    area_solucion: str | None = None,
    audiencia: str | None = None,
    max_resultados: int = 20,
) -> list[dict]:
    """Lista las próximas formaciones en los siguientes N días.

    Args:
        dias: Ventana temporal en días desde hoy (default 30).
        country: Código ISO de país.
        language: Idioma.
        area_solucion: Área de solución.
        audiencia: Sales o Technical.
        max_resultados: Límite de resultados.
    """
    logger.info("listar_proximas_formaciones: dias=%d country=%s", dias, country)
    hoy = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    hasta = (datetime.now(tz=timezone.utc) + timedelta(days=dias)).strftime("%Y-%m-%d")

    feed = await feed_client.get_feed()
    results = filter_feed(
        feed,
        country=country,
        language=language,
        area_solucion=area_solucion,
        audiencia=audiencia,
        desde_fecha=hoy,
        hasta_fecha=hasta,
    )
    # Ascendente para próximas (la más cercana primero)
    results.sort(key=lambda i: i.get("Date") or "")
    return _format_results(results[:max_resultados])


# ---------------------------------------------------------------------------
# Tool 3: detalle_formacion
# ---------------------------------------------------------------------------
@mcp.tool()
async def detalle_formacion(titulo_o_id: str) -> dict | None:
    """Obtiene el detalle completo de una formación por título (parcial) o ID numérico.

    Args:
        titulo_o_id: Título parcial o ID numérico de la formación.
    """
    logger.info("detalle_formacion: titulo_o_id=%r", titulo_o_id)
    feed = await feed_client.get_feed()

    # 1. Buscar por ID exacto
    for item in feed:
        if item.get("ID") == titulo_o_id:
            return item

    # 2. Buscar por título (fuzzy)
    matches = [i for i in feed if fuzzy_match(titulo_o_id, i.get("title", ""))]
    if matches:
        return matches[0]

    return None


# ---------------------------------------------------------------------------
# Tool 4: listar_filtros_disponibles
# ---------------------------------------------------------------------------
@mcp.tool()
async def listar_filtros_disponibles(
    country: str | None = None,
    language: str | None = None,
) -> dict:
    """Lista todos los valores únicos disponibles para cada filtro.
    Opcionalmente pre-filtra por país e idioma para mostrar solo valores relevantes.

    Args:
        country: Pre-filtrar por país.
        language: Pre-filtrar por idioma.
    """
    logger.info("listar_filtros_disponibles: country=%s language=%s", country, language)
    feed = await feed_client.get_feed()
    items = filter_feed(feed, country=country, language=language)

    return {
        "total_formaciones": len(items),
        "paises": sorted({c for i in items for c in i.get("countries", [])}),
        "idiomas": sorted({lang for i in items for lang in i.get("language", [])}),
        "tipos": sorted({i.get("type", "") for i in items if i.get("type")}),
        "formatos": sorted({i.get("format", "") for i in items if i.get("format")}),
        "audiencias": sorted({a for i in items for a in i.get("audience", [])}),
        "areas_solucion": sorted({a for i in items for a in i.get("solution_area", [])}),
        "providers": sorted({i.get("provider", "") for i in items if i.get("provider")}),
        "tecnologias": sorted({t for i in items for t in i.get("technologies", [])}),
    }


# ---------------------------------------------------------------------------
# Tool 5: estadisticas_catalogo
# ---------------------------------------------------------------------------
@mcp.tool()
async def estadisticas_catalogo(
    country: str | None = None,
    language: str | None = None,
) -> dict:
    """Devuelve estadísticas del catálogo: totales por tipo, área, audiencia, etc.

    Args:
        country: Filtrar stats por país.
        language: Filtrar stats por idioma.
    """
    logger.info("estadisticas_catalogo: country=%s language=%s", country, language)
    feed = await feed_client.get_feed()
    items = filter_feed(feed, country=country, language=language)

    dates_with_value = [i.get("Date") for i in items if i.get("Date")]

    return {
        "total": len(items),
        "por_tipo": dict(Counter(i.get("type", "unknown") for i in items)),
        "por_formato": dict(Counter(i.get("format", "unknown") for i in items)),
        "por_area": dict(Counter(a for i in items for a in i.get("solution_area", []))),
        "por_audiencia": dict(Counter(a for i in items for a in i.get("audience", []))),
        "por_provider": dict(Counter(i.get("provider", "unknown") for i in items)),
        "por_idioma": dict(Counter(lang for i in items for lang in i.get("language", []))),
        "rango_fechas": {
            "primera": min(dates_with_value, default=None),
            "ultima": max(dates_with_value, default=None),
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _format_results(items: list[dict]) -> list[dict]:
    """Formatea items del feed para respuesta limpia."""
    return [
        {
            "id": i.get("ID"),
            "titulo": i.get("title"),
            "tipo": i.get("type"),
            "formato": i.get("format"),
            "fecha": i.get("Date"),
            "hora_utc": i.get("datetime_utc"),
            "idiomas": i.get("language"),
            "audiencia": i.get("audience"),
            "area_solucion": i.get("solution_area"),
            "tecnologias": i.get("technologies"),
            "provider": i.get("provider"),
            "paises": i.get("countries"),
            "url": i.get("url"),
            "urls_por_pais": i.get("country_urls"),
        }
        for i in items
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Arranca el servidor MCP con el transporte configurado."""
    logger.info(
        "Starting CloudChampion MCP — transport=%s host=%s port=%d",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
    )
    mcp.run(
        transport=settings.mcp_transport,
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
