"""Dev entry point for `fastmcp dev inspector dev_server.py:mcp`."""

import sys
from pathlib import Path

# Añadir src/ al path para que los imports del paquete funcionen
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_cloudchampion.server import mcp  # noqa: E402, F401
