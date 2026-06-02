## ADDED Requirements

### Requirement: Estructura de directorios Clean Architecture

El backend SHALL organizarse bajo `backend/app/` con una separación estricta por capas: `api/v1/routers/` (transporte HTTP), `services/` (lógica de negocio), `repositories/` (acceso a datos), `models/` (entidades ORM), `schemas/` (DTOs Pydantic), `core/` (configuración y transversales), `integrations/` (clientes externos) y `workers/` (jobs en background). El flujo de dependencia SHALL ser unidireccional Routers → Services → Repositories → Models.

#### Scenario: Existe el árbol de capas completo

- **WHEN** se inspecciona el árbol `backend/app/`
- **THEN** existen los paquetes `api/v1/routers/`, `services/`, `repositories/`, `models/`, `schemas/`, `core/`, `integrations/` y `workers/`
- **AND** cada paquete contiene un `__init__.py` que lo hace importable

#### Scenario: Importabilidad del paquete raíz

- **WHEN** se importa `app` desde el intérprete de Python en el contexto del backend
- **THEN** la importación resuelve sin errores

### Requirement: Slots reservados de transversales

El paquete `core/` SHALL reservar los módulos `security.py`, `permissions.py`, `tenancy.py`, `dependencies.py` y `exceptions.py` como placeholders sin lógica de negocio, para ser completados por changes posteriores (C-02, C-03, C-04). C-01 NO SHALL implementar autenticación, autorización ni resolución de tenant.

#### Scenario: Los slots existen pero están vacíos de lógica

- **WHEN** se inspecciona `backend/app/core/`
- **THEN** existen los archivos `security.py`, `permissions.py`, `tenancy.py`, `dependencies.py` y `exceptions.py`
- **AND** ninguno contiene lógica de auth, RBAC o tenancy (solo placeholder / docstring de intención)

### Requirement: Límite de tamaño de archivo

Cada archivo del backend SHALL no superar las 500 líneas de código (LOC), como convención de mantenibilidad de la Clean Architecture del proyecto.

#### Scenario: Ningún archivo del scaffold excede el límite

- **WHEN** se mide la cantidad de líneas de cualquier archivo `.py` creado en este change
- **THEN** ninguno supera las 500 líneas
