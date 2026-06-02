## ADDED Requirements

### Requirement: Dockerfile multi-stage

El backend SHALL incluir un `Dockerfile` multi-stage con una etapa de build (instalación de dependencias) separada de una etapa de runtime mínima, siguiendo la convención de despliegue de Easypanel. La imagen final SHALL ejecutar la aplicación FastAPI y no SHALL incluir herramientas de build innecesarias en la capa de runtime.

#### Scenario: Build multi-stage produce imagen de runtime

- **WHEN** se construye la imagen a partir del `Dockerfile`
- **THEN** la build pasa por una etapa de dependencias y una etapa final de runtime
- **AND** la imagen final arranca la aplicación FastAPI

### Requirement: Orquestación local con docker-compose

El proyecto SHALL incluir un `docker-compose.yml` que defina, como mínimo, los servicios `api` (la aplicación FastAPI), `postgres` (la base de datos) y `worker` (el proceso de jobs en background). El servicio `api` SHALL depender de `postgres` y SHALL recibir su configuración por variables de entorno.

#### Scenario: Servicios definidos en compose

- **WHEN** se inspecciona `docker-compose.yml`
- **THEN** están definidos los servicios `api`, `postgres` y `worker`
- **AND** `api` declara dependencia sobre `postgres` y consume configuración desde variables de entorno

#### Scenario: Levantar el stack local

- **WHEN** se levanta el stack con docker-compose
- **THEN** el servicio `api` queda disponible y su endpoint `GET /health` responde correctamente
