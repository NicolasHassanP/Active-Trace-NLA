# Tasks — C-08 equipos-docentes

> Strict TDD obligatorio. Para cada task de comportamiento: Safety Net (si toca archivo existente) → RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos: happy + edge) → REFACTOR. Tests con DB real (sin mocks de DB). Pydantic v2 `extra='forbid'`. Identidad SIEMPRE desde el JWT. ≤500 LOC por archivo. Una sola migración (catálogo). Ver `design.md` para las decisiones D1–D10.

## 1. Catálogo RBAC y auditoría (governance MEDIO — surfacear antes de seedear)

- [x] 1.1 RED: test que verifica que el permiso `equipos:ver` existe en el catálogo de permisos del tenant tras el seed/migración (consulta DB real).
- [x] 1.2 GREEN: agregar `equipos:ver` al catálogo de permisos (seed/migración del catálogo, D4). Confirmar política de asociación a roles (OQ-4) antes de asociar.
- [x] 1.3 TRIANGULATE: test de que un rol con `equipos:ver` resuelve el permiso y un rol sin él no (fail-closed).
- [x] 1.4 RED: test que verifica que las claves de auditoría `EQUIPOS_ASIGNACION_MASIVA`, `EQUIPOS_CLONAR`, `EQUIPOS_VIGENCIA_GENERAL` están en el catálogo de acciones (D9).
- [x] 1.5 GREEN: agregar las tres claves al catálogo de auditoría (tabla seedeada o enum, según C-05).
- [x] 1.6 Si el catálogo es tabla seedeada: generar la migración Alembic ÚNICA del change (down_revision = última migración `009_...`) con el alta del permiso y las acciones. No crear más de una migración.

## 2. Schemas Pydantic v2 (`backend/app/schemas/equipo.py`, D10)

- [x] 2.1 RED: test de validación que rechaza campos extra (`extra='forbid'`) en `AsignacionMasivaRequest`.
- [x] 2.2 GREEN: definir `AsignacionMasivaRequest` (lista `usuario_ids`, `materia_id`, `carrera_id`, `cohorte_id`, `rol`, `desde`, `hasta?`, `comisiones`, `responsable_id?`) con `ConfigDict(extra='forbid')`.
- [x] 2.3 GREEN: definir `ClonarEquipoRequest` (origen tripleta, destino tripleta, `desde`, `hasta?`), `VigenciaGeneralRequest` (tripleta, `desde`, `hasta?`), `EquipoQuery` (tripleta + `rol?` + `responsable_id?`).
- [x] 2.4 GREEN: definir respuestas `MisEquiposItem`, `ResumenLote` (`creadas`), `ResumenClonacion` (`clonadas`, `omitidas`), reutilizando `AsignacionRead`/`estado_vigencia` donde aplique.
- [x] 2.5 TRIANGULATE: tests de borde — lista vacía de `usuario_ids` rechazada; `hasta` anterior a `desde` rechazada; tripleta incompleta rechazada.
- [x] 2.6 REFACTOR: extraer un mixin/validator común de tripleta de equipo si hay duplicación; mantener el archivo <500 LOC.

## 3. Repositorio — extensión de `AsignacionRepository` (`backend/app/repositories/usuario_repository.py`, D3/D5)

- [x] 3.1 Safety Net: correr los tests existentes de `AsignacionRepository` (C-07); capturar baseline "{N} passing". Si algo falla → reportar como pre-existente, no corregir.
- [x] 3.2 RED: test (DB real) de `list_by_equipo(materia_id, carrera_id, cohorte_id, rol=None, responsable_id=None)` que filtra por tripleta + tenant + no soft-deleted.
- [x] 3.3 GREEN: implementar `list_by_equipo` reutilizando el scope de tenant heredado de `TenantScopedRepository`.
- [x] 3.4 TRIANGULATE: tests de que el filtro por rol y por responsable acotan, y de que NO devuelve asignaciones de otro tenant ni soft-deleted.
- [x] 3.5 RED: test de `bulk_add(asignaciones)` — `add_all` + un único `commit`, forzando `tenant_id` desde el scope (D5).
- [x] 3.6 GREEN: implementar `bulk_add`; sobrescribir `tenant_id` de cada objeto con el del repo antes de persistir.
- [x] 3.7 TRIANGULATE: test de atomicidad — si la sesión hace rollback ante error, no queda ninguna fila persistida.
- [x] 3.8 RED + GREEN: `bulk_update_vigencia(tripleta, desde, hasta)` que actualiza `desde`/`hasta` de todas las asignaciones activas del equipo y retorna la cantidad afectada.
- [x] 3.9 TRIANGULATE: test de que `bulk_update_vigencia` no toca otros equipos ni otros tenants.
- [x] 3.10 REFACTOR: deduplicar helpers de query por tripleta; confirmar archivo <500 LOC (si se acerca, extraer a un módulo de queries de equipo).

## 4. Servicio — `EquipoService` (`backend/app/services/equipo_service.py`, D3/D5/D6/D7/D9)

- [x] 4.1 RED: test de `listar_mis_equipos(current_user)` que devuelve solo las asignaciones cuyo `usuario_id == current_user.user_id`, con `estado_vigencia` derivado.
- [x] 4.2 GREEN: implementar `listar_mis_equipos` tomando la identidad del `current_user` (JWT), nunca de input externo.
- [x] 4.3 TRIANGULATE: tests — usuario con asignaciones vigentes y vencidas (estados derivados correctos); usuario sin asignaciones (lista vacía); no aparece asignación de otro usuario.
- [x] 4.4 RED: test de `consultar_equipo(query)` que agrupa por tripleta y aplica filtros de rol/responsable.
- [x] 4.5 GREEN + TRIANGULATE: implementar `consultar_equipo`; tests de filtro por rol y aislamiento de tenant.
- [x] 4.6 RED: test de `asignacion_masiva(current_user, req)` — crea N asignaciones atómicamente y emite auditoría `EQUIPOS_ASIGNACION_MASIVA`.
- [x] 4.7 GREEN: implementar `asignacion_masiva`: validar TODOS los `usuario_ids`, contexto y `responsable_id` (mismo tenant) ANTES de persistir; `bulk_add`; auditar (D5/D7/D9). Reusar excepciones C-07 `UsuarioNoEncontrado`/`ReferenciaInvalida`.
- [x] 4.8 TRIANGULATE: tests — atomicidad ante `usuario_id` inexistente (rollback, 0 filas); `responsable_id` de otro tenant rechazado; lote válido crea todas y audita la cantidad.
- [x] 4.9 RED: test de `clonar_equipo(current_user, req)` — duplica vigentes del origen al destino con fechas del destino, omite duplicados, retorna `ResumenClonacion` y audita `EQUIPOS_CLONAR` (D6).
- [x] 4.10 GREEN: implementar `clonar_equipo` (no-destructivo, skip de duplicados por usuario+rol+contexto destino).
- [x] 4.11 TRIANGULATE: tests — clonación normal; re-clonar omite duplicados (idempotencia práctica); equipo origen vacío → 0 clonadas.
- [x] 4.12 RED + GREEN: `modificar_vigencia_general(current_user, req)` — `bulk_update_vigencia`, retorna cantidad afectada, audita `EQUIPOS_VIGENCIA_GENERAL`.
- [x] 4.13 TRIANGULATE: test de que el cambio no afecta otros equipos/tenants y reporta el conteo correcto.
- [x] 4.14 RED + GREEN: `exportar_equipo(query) -> bytes/str CSV` con columnas docente, rol, materia, carrera, cohorte, comisiones, vigencia, `estado_vigencia`; sin PII cifrada (D8).
- [x] 4.15 TRIANGULATE: tests — CSV con una fila por asignación activa; export no cruza tenants; equipo vacío → CSV solo con header.
- [x] 4.16 REFACTOR: extraer construcción de filas/auditoría a helpers; mantener `equipo_service.py` <500 LOC (si supera, separar export a `equipo_export.py`).

## 5. Router — `/api/v1/equipos` (`backend/app/api/v1/routers/equipos.py`, D2/D4)

- [x] 5.1 RED: test de integración (DB real, cliente HTTP) `GET /api/v1/equipos/mis-equipos` → 200 con asignaciones propias; identidad desde JWT.
- [x] 5.2 GREEN: implementar `GET /mis-equipos` con `require_permission("equipos:ver")` y `get_current_user`; nunca leer `usuario_id` de la URL/body.
- [x] 5.3 TRIANGULATE: tests — sin `equipos:ver` → 403 (fail-closed); usuario A no ve equipos de B.
- [x] 5.4 RED + GREEN: `GET /equipos` (consulta por tripleta + filtros) con `require_permission("equipos:ver")`; tests de filtro y aislamiento de tenant.
- [x] 5.5 RED + GREEN: `POST /equipos/asignacion-masiva` con `require_permission("equipos:asignar")`; mapear `UsuarioNoEncontrado`/`ReferenciaInvalida` → 422; éxito → 201 con `ResumenLote`.
- [x] 5.6 TRIANGULATE: tests — sin `equipos:asignar` → 403; referencia inválida → 422 sin crear nada; éxito crea y audita.
- [x] 5.7 RED + GREEN: `POST /equipos/clonar` con `require_permission("equipos:asignar")`; éxito → 200/201 con `ResumenClonacion`.
- [x] 5.8 RED + GREEN: `PATCH /equipos/vigencia-general` con `require_permission("equipos:asignar")`; retorna cantidad afectada.
- [x] 5.9 RED + GREEN: `GET /equipos/exportar` con `require_permission("equipos:ver")` → CSV con `Content-Disposition: attachment`.
- [x] 5.10 TRIANGULATE: test de que export sin permiso → 403 y que el CSV no incluye PII cifrada.
- [x] 5.11 GREEN: montar el router en el agregador de la API v1; verificar prefijo `/api/v1/equipos` y tags.
- [x] 5.12 REFACTOR: extraer helpers de construcción de respuesta; confirmar `equipos.py` <500 LOC.

## 6. Cobertura, cierre y verificación

- [x] 6.1 Correr la suite completa con DB real; confirmar verde y que no se rompió `asignaciones`/C-07 (Safety Net global).
- [x] 6.2 Verificar cobertura ≥80% líneas y ≥90% en la lógica de negocio de `equipo_service.py`.
- [x] 6.3 Revisar reglas duras: tenant scope en todos los queries, fail-closed en todos los endpoints, identidad desde JWT, sin hard delete, `extra='forbid'` en todos los schemas, una sola migración.
- [x] 6.4 Confirmar que las tres acciones de auditoría se emiten en masiva/clonar/vigencia general (test de auditoría con DB real).
- [x] 6.5 Actualizar el TDD Cycle Evidence en el resumen de apply y verificar que las tres Open Questions del proposal quedaron resueltas o confirmadas con negocio.
