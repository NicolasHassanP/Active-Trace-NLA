## Why

Después de encolar un lote de comunicaciones, el PROFESOR no tiene forma de consultar su historial de envíos: el `lote_id` se pierde al navegar fuera de la página y no existe ningún endpoint ni componente UI para listar comunicaciones propias. El docente queda ciego sobre qué envió, cuándo y en qué estado terminó cada mensaje.

## What Changes

- **Nuevo endpoint backend** `GET /api/v1/comunicaciones/mis-envios`: lista las comunicaciones enviadas por el usuario autenticado (resuelto desde JWT), con filtros opcionales por estado (`Pendiente`, `Enviado`, `Error`, `Cancelado`) y paginación offset/limit. Requiere permiso `comunicacion:enviar`. Filtra por `tenant_id` siempre.
- **Nuevo método en repositorio** `ComunicacionRepository.list_by_sender(tenant_id, sender_id, estado?, offset, limit)` — query sobre la tabla `comunicacion` filtrando por `enviado_por` y `tenant_id`.
- **Nuevo schema Pydantic** `MisEnviosResponse` con la lista paginada y metadata de paginación (`total`, `offset`, `limit`, `items`).
- **Nuevo componente frontend** `ComunicacionesHistorial`: tabla/lista con filtro de estado y paginación que consume el nuevo endpoint vía TanStack Query.
- **Actualización de `ComunicacionesPage`**: agrega tabs "Componer" | "Historial" para mostrar composición y el historial en la misma ruta `/comunicaciones`.
- **Actualización de spec `comunicaciones`**: agrega el requisito de consulta del historial propio.
- **Actualización de spec `comunicaciones-frontend`**: agrega el requisito de la tab "Historial" y el componente `ComunicacionesHistorial`.

## Capabilities

### New Capabilities

- `comunicaciones-historial-sender`: Capacidad de consultar el historial de comunicaciones propias del usuario autenticado, con filtros por estado y paginación. Cubre el endpoint `GET /mis-envios`, el método `list_by_sender` en el repositorio, el schema de respuesta paginada, y el componente frontend `ComunicacionesHistorial`.

### Modified Capabilities

- `comunicaciones`: Se agrega un nuevo requisito de consulta del historial por remitente autenticado (el spec existente solo cubre persistencia, estados y preview; no cubre consulta).
- `comunicaciones-frontend`: Se agrega el requisito de la tab "Historial" en `ComunicacionesPage` y el componente `ComunicacionesHistorial`.

## Impact

- **Backend**: `backend/app/repositories/comunicacion_repository.py` (nuevo método), `backend/app/routers/comunicaciones.py` (nuevo endpoint), `backend/app/schemas/comunicacion.py` (nuevo schema de respuesta paginada).
- **Frontend**: `frontend/src/features/comunicaciones/components/ComunicacionesHistorial.tsx` (nuevo), `frontend/src/features/comunicaciones/pages/ComunicacionesPage.tsx` (agregar tabs), `frontend/src/features/comunicaciones/services/comunicacionesService.ts` o hook TanStack Query para `mis-envios`.
- **Sin cambios de schema de BD**: el campo `enviado_por` ya existe en la tabla `comunicacion`; no se requiere migración Alembic.
- **Sin breaking changes**: el endpoint es aditivo; los endpoints existentes no cambian.
- **Dependencias**: C-12 (comunicaciones-cola-worker, archivado — modela la tabla y el repositorio base), C-22 (frontend-academico-docente, archivado — provee la estructura de features/comunicaciones).
