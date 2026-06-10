## Context

El JWT lleva en `sub` el `auth_identities.id`. `get_current_user` lo expone como `CurrentUser.user_id`. La tabla de dominio `usuario` tiene su propio PK (`usuario.id`) y una columna `auth_identity_id` que apunta a la identidad de auth. **Todas las FKs de negocio referencian `usuario.id`**, no `auth_identities.id`. El puente correcto es `resolve_domain_user_id(current_user, db)` (en `backend/app/core/dependencies.py`), que hace `SELECT usuario.id WHERE auth_identity_id = current_user.user_id AND tenant_id = ... AND deleted_at IS NULL` y falla cerrado con 500 si no existe.

Este puente se introdujo en C-27 y se aplicó parcialmente change por change. Una auditoría con `grep current_user.user_id` sobre `backend/app/api/v1/routers/` y `backend/app/services/` revela que la mayoría de módulos ya están correctos (comunicaciones, calificaciones-router, tareas, perfil, coloquios, aviso-ack-write), pero quedan **usos residuales en lectura/filtro y fallbacks** que persisten o filtran `auth_identity_id` donde la DB espera `usuario.id`. Governance del dominio: **ALTO** (identidad/auth en múltiples módulos).

### Clasificación de la auditoría (estado actual)

**Correcto — no tocar:**
- `auth.py:247,261` → `_identity_repo.get_by_id(current_user.user_id)` opera sobre `auth_identities` (correcto).
- `audit_service.py` / `audit.actor_user_id` → guarda `auth_identities.id` **por diseño** (RN-41/D5). Excepción documentada.
- `auditoria.py:88` → `actor_filter = current_user.user_id` filtra `evento_auditoria.actor_user_id`, que almacena `auth_identities.id` → consistente con el writer.

**Bug confirmado — corregir:**
- `avisos.py:155,182` → pasa `current_user.user_id` a `listar_feed`/`listar_pendientes`; el service joinea acks por `usuario.id`. El feed marca "leído/no leído" contra el ack del usuario equivocado.
- `encuentro_service.py:232,258` y `guardia_service.py:107,186` → `_asig_repo.list(usuario_id=current_user.user_id)`; `Asignacion.usuario_id` es FK a `usuario.id` (confirmado en `models/usuario.py:148-150`).
- `padron_service.py:179` → ownership check `version.cargado_por != current_user.user_id`; `cargado_por` es `usuario.id`.

**Fallback latente — endurecer:**
- `domain_user_id or current_user.user_id` en `calificacion_service.py:224`, `equipo_service.py:77`, `padron_service.py:114`, `alumno_service.py:89`, `analisis_service.py` (varias). El router siempre resuelve `domain_user_id`, así que el fallback nunca se usa hoy, pero enmascara el bug y permite regresiones: hacer el parámetro requerido.

## Goals / Non-Goals

**Goals:**
- Cerrar el invariante de identidad de forma transversal: ninguna columna FK a `usuario.id` recibe `auth_identity_id`.
- Endurecer las firmas de services para que `domain_user_id` sea requerido (sin fallback).
- Documentar el invariante (incluida la excepción de auditoría) para futuros agentes.
- Tests de regresión por módulo, con DB real (regla dura #4), que prueben que el flujo existente sigue funcionando.

**Non-Goals:**
- No cambiar firmas de endpoints HTTP ni contratos de API (request/response Pydantic intactos).
- No tocar schema de DB ni crear migraciones (no hay cambio de columnas).
- No re-diseñar el modelo de auditoría: `actor_user_id = auth_identities.id` se mantiene por diseño.
- No introducir un helper nuevo de resolución: `resolve_domain_user_id` ya es el patrón canónico.

## Decisions

**D1 — Resolver en el router, propagar `domain_user_id` al service.**
El router (que tiene acceso a `db` y `current_user`) llama `resolve_domain_user_id` una vez y pasa `domain_user_id` al service. Alternativa descartada: resolver dentro del service (requeriría inyectar `current_user` + query extra en cada método y dispersaría la lógica de auth en la capa de dominio). El patrón router-resuelve ya está establecido en comunicaciones/tareas/coloquios; se mantiene por consistencia.

**D2 — `domain_user_id` requerido, sin fallback.**
Eliminar `domain_user_id or current_user.user_id`. Hacer el parámetro `domain_user_id: uuid.UUID` (sin default). Rationale: el fallback es una bomba de tiempo — si un futuro caller omite la resolución, el bug reaparece silencioso en producción. Mejor fallar en import/llamada que corromper datos. Alternativa descartada: mantener el fallback "por compatibilidad" → contradice la regla dura #8/#14.

**D3 — Auditoría queda como excepción explícita y documentada, no se "corrige".**
`audit.actor_user_id` guarda `auth_identities.id` por decisión de diseño (RN-41/D5): la auditoría rastrea la *identidad de autenticación* real (incluida impersonación), no el usuario de dominio. Se documenta para que nadie lo "arregle" por error. Alternativa descartada: migrar auditoría a `usuario.id` → rompería la semántica de impersonación y la trazabilidad de identidad.

**D4 — Tests sin mocks de DB, uno por módulo afectado.**
Cada fix lleva un test de regresión que (a) crea un `auth_identity` + su `usuario` con IDs distintos, (b) ejecuta el endpoint/service, (c) verifica que la columna escrita/filtrada contiene `usuario.id` y no `auth_identity_id`. Tener IDs distintos es clave: si fueran iguales el test no probaría nada (tautología — prohibido por Strict TDD).

**D5 — Documentar en `docs/ARQUITECTURA.md` + `CLAUDE.md`.**
Sección nueva "Identidad: dominio vs. auth" con la tabla de cuándo usar cada ID, el snippet de `resolve_domain_user_id`, y la excepción de auditoría. `CLAUDE.md` lo referencia como regla dura adicional para que sea lo primero que un agente lee.

## Risks / Trade-offs

- **[Falso positivo: marcar como bug algo correcto]** → Mitigación: la auditoría clasifica cada hit en correcto/bug/fallback con evidencia del modelo (FK confirmada). Solo se tocan los hits con FK a `usuario.id` verificada.
- **[Tests con IDs iguales (auth_identity_id == usuario.id) no prueban nada]** → Mitigación: D4 exige IDs distintos explícitos en cada fixture; revisar en code review que el assert compara contra `usuario.id` y que difiere de `auth_identity_id`.
- **[Romper un flujo existente al endurecer la firma]** → Mitigación: el router ya resuelve `domain_user_id` en todos los callers actuales; el safety-net (correr tests existentes del módulo antes de modificar) detecta cualquier caller que dependiera del fallback.
- **[Quedar usos no detectados por el grep]** → Mitigación: la auditoría busca también nombres de columna (`cargado_por`, `importado_por`, `usuario_id=`, `asignado_por`, etc.), no solo `current_user.user_id`, para cubrir indirecciones.

## Migration Plan

1. **Auditoría** (task 1): consolidar la lista definitiva de hits y su clasificación; congelar el alcance.
2. **Fix por módulo** (tasks 2..N), cada uno con su safety-net + RED/GREEN/triangulación:
   - avisos (feed/pendientes), encuentros, guardias, padron (ownership), y endurecimiento de fallbacks en calificacion/equipo/padron/alumno/analisis.
3. **Documentación** (task final): `docs/ARQUITECTURA.md` + `CLAUDE.md`.
4. **Verificación global**: correr la suite backend completa; confirmar 0 usos de `current_user.user_id` en columnas de dominio (grep de cierre).

Rollback: cada módulo es un fix aislado y revertible por commit; no hay cambio de datos persistidos ni de schema, así que revertir el código restaura el comportamiento previo sin migración inversa.

## Open Questions

- Ninguna bloqueante. La excepción de auditoría está cerrada por D3. Si durante la auditoría aparece un módulo no listado (p. ej. inbox, programas, fechas_academicas) con escritura de FK de dominio vía `current_user.user_id`, se agrega como sub-task del fix sistemático sin re-proponer.
