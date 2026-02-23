// ---------------------------------------------------------------------------
// Infraestructura Azure para CloudChampion MCP Server
// Recursos: ACR + Log Analytics + Container Apps Environment + Container App
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

// ── Parámetros ─────────────────────────────────────────────────────────────

@description('Ubicación de los recursos')
param location string = resourceGroup().location

@description('Nombre del Azure Container Registry (debe ser globalmente único, solo alfanumérico)')
@minLength(5)
@maxLength(50)
param acrName string

@description('Nombre del Container Apps Environment')
param environmentName string = 'env-cloudchampion-mcp'

@description('Nombre de la Container App')
param appName string = 'mcp-cloudchampion'

@description('Imagen Docker (repo:tag). Si es la primera vez, se usará una imagen placeholder.')
param containerImage string = ''

@description('CPU asignada a la Container App')
param cpu string = '0.25'

@description('Memoria asignada a la Container App')
param memory string = '0.5Gi'

@description('Mínimo de réplicas (0 = scale to zero)')
@minValue(0)
@maxValue(10)
param minReplicas int = 0

@description('Máximo de réplicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('TTL de la caché del feed en segundos')
param cacheTtlSeconds string = '600'

@description('Nivel de logging: DEBUG, INFO, WARNING, ERROR')
@allowed(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
param logLevel string = 'INFO'

// ── Azure Container Registry ───────────────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ── Log Analytics Workspace (requerido por Container Apps Environment) ──────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${appName}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ── Container Apps Environment ─────────────────────────────────────────────

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ── Container App ──────────────────────────────────────────────────────────

// Solo desplegar la Container App si tenemos una imagen real
var hasImage = !empty(containerImage)
var imageToUse = hasImage ? '${acr.properties.loginServer}/${containerImage}' : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: hasImage ? [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ] : []
      secrets: hasImage ? [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: appName
          image: imageToUse
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            { name: 'MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'MCP_HOST', value: '0.0.0.0' }
            { name: 'MCP_PORT', value: '8000' }
            { name: 'CACHE_TTL_SECONDS', value: cacheTtlSeconds }
            { name: 'CLOUDCHAMPION_FEED_URL', value: 'https://www.cloudchampion.es/wp-json/feed/content' }
            { name: 'LOG_LEVEL', value: logLevel }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// ── Outputs ────────────────────────────────────────────────────────────────

@description('FQDN de la Container App')
output appFqdn string = app.properties.configuration.ingress.fqdn

@description('URL completa del MCP endpoint')
output mcpEndpoint string = 'https://${app.properties.configuration.ingress.fqdn}/mcp'

@description('Login server del ACR')
output acrLoginServer string = acr.properties.loginServer

@description('Nombre del ACR')
output acrName string = acr.name

@description('Nombre de la Container App')
output appName string = app.name
