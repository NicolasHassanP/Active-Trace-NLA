## Why

Hoy cada usuario depende de un ADMIN para corregir sus propios datos (banco, CBU, regional, email): no puede mantener su perfil al día, lo que retrasa liquidaciones que llegan a cuentas erróneas o desactualizadas (RN-26, HU-42). En paralelo, no existe ningún canal de comunicación interna entre los usuarios registrados del sistema: coordinación, el propio sistema y los docentes carecen de una bandeja para conversar fuera del flujo de emails salientes a alumnos (FL-10, F3.4, HU-13). Este change cierra ambos huecos de la Épica 11 sobre la identidad base (`Usuario`, E4) ya creada en C-07.

## What Changes

- **Perfil propio (F11.1, HU-42)**: un endpoint `GET/PATCH /api/v1/perfil` que permite a cualquier usuario autenticado ver y editar **sus propios** datos: `nombre`, `apellidos`, `dni`, `sexo`/`genero`, `banco`, `cbu`, `alias_cbu`, `regional`, `email`, `facturador` (modalidad de cobro) y `legajo_profesional`.
  - El `cuil` es de **solo lectura** (S6): se deriva/gestiona fuera del perfil y nunca es editable por el usuario.
  - La identidad del usuario a editar SIEMPRE se deriva del JWT — jamás de un `usuario_id` en la URL o el body. No hay forma de editar el perfil de otro.
  - El cambio de `email` respeta la unicidad `(tenant_id, email)` por blind index ya establecida en `usuarios`.
- **Mensajería interna (F3.4, F11.2, FL-10, HU-13)**: nuevo módulo de bandeja entre usuarios registrados del sistema, **paralelo e independiente** del módulo `comunicaciones` (emails salientes a alumnos).
  - Modelo de hilos: un `HiloMensaje` agrupa `Mensaje`s entre participantes; cada mensaje tiene asunto, cuerpo, remitente y marca temporal.
  - `GET /api/v1/inbox` (hilos del usuario), `GET /api/v1/inbox/{hilo_id}` (mensajes del hilo), `POST /api/v1/inbox/{hilo_id}/responder` (responder dentro del hilo) y `POST /api/v1/inbox` (iniciar un hilo nuevo).
  - Marcado de leído/no leído por destinatario; conteo de no leídos.
  - Aislamiento por usuario y por tenant: un usuario solo ve hilos en los que participa, dentro de su tenant.
- **Soft delete** en hilos/mensajes (auditoría append-only); el remitente real queda siempre atribuido (sin spoofing).
- El cierre de sesión (F11.3, HU-43) **NO** se reimplementa aquí: reusa el logout ya provisto por C-03.

## Capabilities

### New Capabilities
- `perfil-usuario`: ver y editar el perfil propio del usuario autenticado (datos personales, fiscales, bancarios y de contacto), con `cuil` de solo lectura, identidad derivada del JWT y PII cifrada en reposo.
- `mensajeria-interna`: bandeja de mensajería interna entre usuarios registrados del sistema, organizada en hilos, con envío/respuesta, marcado de leído y aislamiento por usuario y tenant.

### Modified Capabilities
<!-- Ninguna. El perfil reusa la entidad Usuario (E4) y las reglas de PII/unicidad ya definidas en la capability `usuarios` (C-07) sin cambiar sus requisitos. -->

## Impact

- **Backend**:
  - Nuevo router `perfil` (`/api/v1/perfil`) sobre `Usuario` existente; nuevos schemas `PerfilRead` / `PerfilUpdate` (Pydantic v2, `extra='forbid'`, `cuil` read-only).
  - Nuevo módulo `mensajeria`: modelos `HiloMensaje` y `Mensaje` (+ tabla de participantes/estado-leído), repositorios con scope por tenant + participante, servicio y router `inbox`.
  - Una migración Alembic para las tablas de mensajería (hilos, mensajes, participantes) con `tenant_id` y soft delete.
- **Seguridad**: `require_permission("perfil:editar")` para el PATCH de perfil y `require_permission("inbox:usar")` para la mensajería (fail-closed); identidad siempre del JWT. PII (`dni`, `cbu`, `alias_cbu`) reusa el cifrado AES-256 ya implementado en `usuarios`.
- **Frontend** (fuera del scope de implementación de este change backend-first; consumido luego por el shell C-21): contratos `/api/v1/perfil` e `/api/v1/inbox/*` quedan estables.
- **Dependencias**: requiere C-07 `usuarios-y-asignaciones` (entidad `Usuario`, cifrado PII, RBAC). No bloquea el camino crítico.
