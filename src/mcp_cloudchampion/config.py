"""Configuración del MCP Server por variables de entorno."""

from __future__ import annotations

import json
import logging
import os
import sys


class Settings:
    """Configuración leída de variables de entorno con valores por defecto."""

    def __init__(self) -> None:
        self.feed_url: str = os.getenv(
            "CLOUDCHAMPION_FEED_URL",
            "https://www.cloudchampion.es/wp-json/feed/content",
        )
        self.cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
        self.mcp_transport: str = os.getenv("MCP_TRANSPORT", "streamable-http")
        self.mcp_host: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.mcp_port: int = int(os.getenv("MCP_PORT", "8000"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()


def setup_logging() -> None:
    """Configura logging estructurado (JSON en producción, texto en dev)."""

    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_obj = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info and record.exc_info[0] is not None:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj, ensure_ascii=False)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        handlers=[handler],
        force=True,
    )
