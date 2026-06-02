## ADDED Requirements

### Requirement: Configuración tipada desde el entorno

El sistema SHALL cargar su configuración mediante un objeto `Settings` basado en Pydantic v2 (`pydantic-settings`), poblado desde variables de entorno y/o un archivo `.env`. La configuración SHALL estar tipada y validarse en el arranque; un valor inválido o una variable requerida ausente SHALL impedir que la aplicación inicie.

#### Scenario: Carga válida desde el entorno

- **WHEN** las variables de entorno requeridas están presentes y son válidas
- **THEN** el objeto `Settings` se instancia exitosamente con valores tipados

#### Scenario: Configuración inválida o incompleta

- **WHEN** falta una variable requerida o un valor no satisface su tipo
- **THEN** la validación de `Settings` falla en el arranque con un error claro
- **AND** la aplicación no inicia con configuración inválida

### Requirement: Contrato de variables de entorno base

La configuración SHALL definir, como mínimo, las variables base del proyecto: `DATABASE_URL` (conexión PostgreSQL), `SECRET_KEY` (firma JWT, mínimo 32 caracteres), `ENCRYPTION_KEY` (AES-256, exactamente 32 caracteres) y `ACCESS_TOKEN_EXPIRE_MINUTES` (con valor por defecto 15). Estas variables SHALL estar documentadas en un archivo `.env.example` versionado, sin valores secretos reales.

#### Scenario: Existe la plantilla de entorno

- **WHEN** se inspecciona el repositorio del backend
- **THEN** existe un `.env.example` que lista las variables base con descripciones o valores de ejemplo no sensibles

#### Scenario: Default del tiempo de expiración del access token

- **WHEN** no se provee `ACCESS_TOKEN_EXPIRE_MINUTES`
- **THEN** `Settings` adopta el valor por defecto de 15 minutos
