# CloudChampion MCP Server

Servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) para consultar el catálogo de formación de **Cloud Champion** ([cloudchampion.es](https://www.cloudchampion.es) y variantes por país).

Expone herramientas que permiten a agentes de IA buscar, filtrar y obtener estadísticas sobre webinars, vídeos, learning paths, podcasts y otros recursos de Microsoft para partners.

## Arquitectura

```
Agente IA ──► MCP Server (FastMCP) ──► API Cloud Champion
                  │                     /wp-json/feed/content
                  │
                  └── Caché en memoria (TTL configurable)
```

- **Feed API**: `GET https://www.cloudchampion.es/wp-json/feed/content` — catálogo global público (todos los países/idiomas)
- **Caché**: En memoria con TTL de 10 min (configurable) para evitar llamadas excesivas
- **Búsqueda**: Fuzzy matching sin tildes/diacríticos para español y otros idiomas
- **Transporte**: Streamable HTTP (default), SSE o stdio

## Herramientas disponibles (Tools)

| Tool | Descripción |
|---|---|
| `buscar_formacion` | Búsqueda textual + filtros combinables (país, idioma, tipo, audiencia, área, provider, fechas) |
| `listar_proximas_formaciones` | Formaciones futuras en una ventana de N días |
| `detalle_formacion` | Detalle completo de una formación por título parcial o ID |
| `listar_filtros_disponibles` | Valores únicos disponibles para cada filtro (tipos, áreas, idiomas, etc.) |
| `estadisticas_catalogo` | Estadísticas del catálogo: totales por tipo, área, audiencia, provider, rango de fechas |

## Desarrollo local

### Requisitos

- Python 3.11+
- pip

### Instalación

```bash
# Clonar el repositorio
git clone <repo-url>
cd cloudchampion-mcp

# Instalar dependencias
pip install -r requirements.txt

# (Opcional) Copiar y ajustar variables de entorno
cp .env.example .env
```

### Modo desarrollo con inspector web

```bash
fastmcp dev src/mcp_cloudchampion/server.py
```

Esto abre el inspector web de FastMCP donde puedes probar las tools interactivamente.

### Modo stdio (para uso local con clientes MCP)

```bash
MCP_TRANSPORT=stdio python -m mcp_cloudchampion.server
```

### Modo HTTP (para acceso remoto)

```bash
python -m mcp_cloudchampion.server
# Servidor en http://0.0.0.0:8000
```

## Docker

### Build

```bash
docker build -t mcp-cloudchampion .
```

### Run

```bash
docker run -p 8000:8000 mcp-cloudchampion
```

### Con variables de entorno custom

```bash
docker run -p 8000:8000 \
  -e CACHE_TTL_SECONDS=300 \
  -e LOG_LEVEL=DEBUG \
  mcp-cloudchampion
```

## Despliegue en Azure Container Apps

La infraestructura se define como **IaC con Bicep** en la carpeta `infra/`.

### 1. Crear infraestructura con Bicep

```bash
RESOURCE_GROUP="rg-cloudchampion-mcp"
LOCATION="westeurope"

# Crear Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Desplegar infraestructura (ACR + Log Analytics + Container Apps Env + Container App)
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Ver outputs (FQDN, MCP endpoint, ACR login server)
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query 'properties.outputs' -o json
```

Recursos creados:
- **Azure Container Registry** (Basic SKU, admin habilitado)
- **Log Analytics Workspace** (retención 30 días)
- **Container Apps Environment** (con logging a Log Analytics)
- **Container App** (scale to zero, 0.25 vCPU, 0.5 GiB RAM, ingress HTTP externo)

### 2. Build & Deploy de la imagen

```bash
ACR_NAME="acrcloudchampionmcp"
ACA_APP="mcp-cloudchampion"

# Build imagen en ACR
az acr build --registry $ACR_NAME --image mcp-cloudchampion:latest .

# Actualizar Container App con la nueva imagen
az containerapp update \
  --name $ACA_APP \
  --resource-group $RESOURCE_GROUP \
  --image "$ACR_NAME.azurecr.io/mcp-cloudchampion:latest"
```

### 3. Obtener URL

```bash
az containerapp show --name $ACA_APP --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

### Personalizar parámetros

Edita `infra/main.parameters.json` para cambiar el nombre del ACR, CPU, memoria, réplicas, etc. Parámetros disponibles:

| Parámetro | Descripción | Default |
|---|---|---|
| `acrName` | Nombre del ACR (globalmente único) | `acrcloudchampionmcp` |
| `environmentName` | Nombre del Container Apps Environment | `env-cloudchampion-mcp` |
| `appName` | Nombre de la Container App | `mcp-cloudchampion` |
| `minReplicas` | Mín. réplicas (0 = scale to zero) | `0` |
| `maxReplicas` | Máx. réplicas | `3` |
| `cpu` | CPU asignada | `0.25` |
| `memory` | Memoria asignada | `0.5Gi` |
| `cacheTtlSeconds` | TTL de caché del feed | `600` |
| `logLevel` | Nivel de logging | `INFO` |

### CI/CD

El workflow de GitHub Actions (`.github/workflows/deploy.yml`) tiene dos jobs:

1. **infra** — Despliega Bicep (solo si cambian ficheros en `infra/` o se lanza manualmente con `deploy_infra: true`)
2. **build-and-deploy** — Build de imagen en ACR + deploy a Container App (en cada push a `main`)

Requiere el secret `AZURE_CREDENTIALS` configurado en el repo.

## Consumir el MCP

### Desde VS Code / Claude Desktop

```json
{
  "mcpServers": {
    "cloudchampion": {
      "url": "https://<tu-aca-url>.azurecontainerapps.io/mcp"
    }
  }
}
```

### Desde un agente Python

```python
from agents import Agent
from agents.mcp import MCPServerStreamableHttp

mcp = MCPServerStreamableHttp(url="https://<tu-aca-url>.azurecontainerapps.io/mcp")

agent = Agent(
    name="CloudChampionAssistant",
    instructions="Eres un asistente experto en formación de Cloud Champion...",
    mcp_servers=[mcp],
)
```

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `CLOUDCHAMPION_FEED_URL` | URL del feed de contenido | `https://www.cloudchampion.es/wp-json/feed/content` |
| `CACHE_TTL_SECONDS` | TTL de la caché en segundos | `600` |
| `MCP_TRANSPORT` | Transporte: `streamable-http`, `sse`, `stdio` | `streamable-http` |
| `MCP_HOST` | Host de escucha | `0.0.0.0` |
| `MCP_PORT` | Puerto de escucha | `8000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

## Estructura del proyecto

```
├── src/
│   └── mcp_cloudchampion/
│       ├── __init__.py        # Versión del paquete
│       ├── __main__.py        # python -m entry point
│       ├── config.py          # Settings + logging setup
│       ├── text_utils.py      # Normalización de texto / fuzzy match
│       ├── feed_client.py     # Cliente HTTP + caché con TTL
│       ├── filters.py         # Motor de filtrado
│       └── server.py          # FastMCP server + 5 tools
├── Dockerfile                 # Multi-stage build
├── .dockerignore
├── .env.example
├── pyproject.toml
├── requirements.txt
├── README.md
└── .github/workflows/
    └── deploy.yml             # CI/CD → Azure Container Apps
```

## Licencia

MIT
