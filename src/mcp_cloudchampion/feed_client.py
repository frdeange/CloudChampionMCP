"""Cliente HTTP para la API de Cloud Champion con caché en memoria + TTL."""

from __future__ import annotations

import logging
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class FeedClient:
    """Singleton que obtiene y cachea el feed completo de formaciones."""

    def __init__(self) -> None:
        self._cache: list[dict] | None = None
        self._cache_timestamp: float = 0.0

    async def get_feed(self, force_refresh: bool = False) -> list[dict]:
        """Devuelve el feed completo, usando caché si no ha expirado.

        Args:
            force_refresh: Forzar recarga ignorando la caché.

        Returns:
            Lista de items del catálogo de formación.
        """
        now = time.time()

        if (
            not force_refresh
            and self._cache is not None
            and (now - self._cache_timestamp) < settings.cache_ttl_seconds
        ):
            age = round(now - self._cache_timestamp, 1)
            logger.debug("Cache hit — edad: %ss, TTL: %ss", age, settings.cache_ttl_seconds)
            return self._cache

        logger.info(
            "Fetching feed from %s (force_refresh=%s)", settings.feed_url, force_refresh
        )
        start = time.monotonic()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(settings.feed_url)
            response.raise_for_status()
            data = response.json()

        elapsed = round(time.monotonic() - start, 2)
        logger.info("Feed loaded: %d items in %ss", len(data), elapsed)

        self._cache = data
        self._cache_timestamp = time.time()
        return self._cache


# Singleton global
feed_client = FeedClient()
