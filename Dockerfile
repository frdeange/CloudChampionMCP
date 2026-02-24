# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /install /usr/local

# Variables de entorno por defecto
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    CACHE_TTL_SECONDS=600 \
    CLOUDCHAMPION_FEED_URL=https://www.cloudchampion.es/wp-json/feed/content \
    LOG_LEVEL=INFO

EXPOSE 8000

# Health check usando urllib (disponible en python slim sin deps extra)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Punto de entrada: FastMCP en modo Streamable HTTP
CMD ["python", "-m", "mcp_cloudchampion.server"]
