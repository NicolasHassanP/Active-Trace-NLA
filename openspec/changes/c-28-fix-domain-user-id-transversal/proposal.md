## Why

`CurrentUser.user_id` (en `backend/app/core/dependencies.py`) es el `auth_identities.id` — el `sub` del JWT. Pero **todas las FKs de dominio** (`tarea.asignado_por`, `comunicacion.enviado_por`, `comentario_tarea.autor_id`, `padron_version.cargado_por`, `Asignacion.usuario_id`, `acknowledgment_aviso.usuario_id`, etc.) referencian `usuario.id`. Estos dos identificadores son tablas distintas; usar uno donde la DB espera el otro produce datos corruptos silenciosos: registros atribuidos a un UUID que no existe en `usuario`, scopes "propio" que nunca matchean, y violaciones de FK intermitentes.

El puente correcto ya existe: `resolve_domain_user_id(current_user, db)` traduce `auth_identities.id → usuario.id`. Algunos módulos ya lo aplican (comunicaciones, calificaciones, tareas, perfil, coloquios, avisos-ack), pero el patrón se introdujo change por change y **quedaron usos residuales de `current_user.user_id` en contextos de dominio** repartidos por routers y services. Es un defecto sistémico de identidad (regla dura #8/#14, governance ALTO): hay que auditarlo de forma transversal y cerrarlo de una vez, con tests de regresión que impidan que vuelva a aparecer.

## What Changes

- **Auditoría transversal** de `routers/` y `services/` para clasificar cada uso de `current_user.user_id` como (a) correcto, (b) bug de dominio a corregir, o (c) excepción documentada (atribución de auditoría).
- **Fix sistemático** aplicando `resolve_domain_user_id()` en el router y propagando `domain_user_id` al service en cada punto de escritura/filtro de FK de dominio detectado:
  - `avisos.py` — `listar_feed` / `listar_pendientes` reciben `usuario_id` que se joinea contra acks por `usuario.id`; hoy reciben `auth_identity_id`.
  - `encuentro_service.py`, `guardia_service.py` — `_asig_repo.list(usuario_id=current_user.user_id)` contra `Asignacion.usuario_id` (FK a `usuario.id`).
  - **Eliminar los fallbacks `domain_user_id or current_user.user_id`** en `calificacion_service.py`, `equipo_service.py`, `padron_service.py`, `alumno_service.py`, `analisis_service.py`: el fallback enmascara el bug y debe ser un parámetro requerido.
  - `padron_service.py` — ownership check `version.cargado_por != current_user.user_id` compara contra columna `usuario.id`.
- **Documentar el invariante** en `docs/ARQUITECTURA.md` y la KB: "FKs de dominio = `usuario.id`; identidad de auditoría = `auth_identities.id`; el puente es `resolve_domain_user_id`". Incluir la excepción explícita de `audit.actor_user_id` (que SÍ guarda el `auth_identities.id` por diseño, RN-41/D5).
- **Tests de regresión** por módulo afectado que confirmen que la escritura/lectura usa `usuario.id` y que el flujo existente no se rompe.

No hay cambios de schema ni de API pública: las firmas de endpoint no cambian, solo el valor que se persiste/filtra internamente.

## Capabilities

### New Capabilities
- `identidad-dominio-vs-auth`: invariante transversal que define cuándo usar `usuario.id` (FKs de dominio) vs `auth_identities.id` (identidad de auditoría), el rol de `resolve_domain_user_id` como único puente, y la prohibición de persistir/filtrar `current_user.user_id` directamente en columnas que referencian `usuario.id`.

### Modified Capabilities
<!-- Sin cambios a requisitos de specs existentes: este change corrige el cumplimiento del invariante de identidad ya establecido (C-03/C-07), no redefine comportamiento de las capabilities de cada módulo. -->

## Impact

- **Routers**: `avisos.py` (verificar/corregir feed y pendientes); auditoría de `equipos.py`, `padron.py`, `analisis.py`, `alumno.py`, `encuentros.py`, `guardias.py` para confirmar que el router resuelve `domain_user_id` antes de delegar.
- **Services**: `aviso_service.py`, `encuentro_service.py`, `guardia_service.py`, `calificacion_service.py`, `equipo_service.py`, `padron_service.py`, `alumno_service.py`, `analisis_service.py` — eliminar fallbacks a `current_user.user_id` y exigir `domain_user_id`.
- **Sin cambios**: `auth.py` (usa correctamente `auth_identities.id` vía `_identity_repo`), `audit_service.py` / `audit.actor_user_id` (excepción documentada — guarda la identidad del JWT por diseño).
- **Docs**: `docs/ARQUITECTURA.md` + `CLAUDE.md`/KB — nueva sección sobre el invariante de identidad de dominio.
- **Tests**: nuevos tests de regresión por módulo; sin mocks de DB (regla dura #4).
- **Governance**: ALTO (toca identidad en múltiples módulos). Cada fix se acompaña de test que prueba que el flujo existente sigue verde.
