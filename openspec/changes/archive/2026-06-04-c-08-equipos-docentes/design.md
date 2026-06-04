## Context

C-07 (`usuarios-y-asignaciones`) ya entregó el modelo `Asignacion` (`backend/app/models/usuario.py`), su repositorio `AsignacionRepository` con scope de tenant (`backend/app/repositories/usuario_repository.py`), el `AsignacionService` y el CRUD unitario en `/api/v1/asignaciones`. La spec `asignaciones` cubre: vínculo usuario↔rol↔contexto, multi-rol, vigencia temporal con `estado_vigencia` derivado (RN-10), jerarquía `responsable_id` (RN-11) y CRUD protegido por `equipos:asignar` con aislamiento multi-tenant.

C-08 NO reescribe nada de eso: agrega la **capa de operaciones de equipo** que negocio necesita (FL-03, épica F4): mis-equipos, consulta agrupada, asignación masiva, clonación entre cohortes (RN-12), vigencia general y exportación. El "equipo" no es una entidad nueva: es el conjunto de asignaciones que comparten la tripleta `(materia_id, carrera_id, cohorte_id)`.

**Restricciones del proyecto (reglas duras)**: Clean Architecture Routers→Services→Repositories→Models; multi-tenancy row-level (repos filtran por tenant por defecto); RBAC fino fail-closed; soft delete; ≤500 LOC por archivo; Pydantic v2 `extra='forbid'`; una sola migración Alembic por change; tests con DB real (sin mocks de DB); Strict TDD. Identidad SIEMPRE desde el JWT.

**Governance**: dominio de equipos = MEDIO (lógica de dominio sobre asignaciones). Las operaciones tocan el eje de autorización contextual (asignaciones determinan permisos efectivos), por lo que se implementa con checkpoints y se surfacean las decisiones no obvias (las tres Open Questions). No se escribe RBAC ni auth nuevos: solo se consume.

## Goals / Non-Goals

**Goals:**
- Vista de "mis equipos" de solo lectura para el usuario autenticado (F4.2 / HU-17).
- Consulta de equipo agrupado por `(materia, carrera, cohorte)` con filtros (F4.3).
- Asignación masiva atómica de N docentes a una tripleta + rol (F4.4 / HU-18 / RN-30).
- Clonación de equipo entre cohortes, no-destructiva, con skip de duplicados (F4.5 / HU-19 / RN-12).
- Modificación de vigencia general en bloque (F4.6 / HU-20).
- Exportación CSV del equipo (F4.7).
- Auditoría de las operaciones en bloque.
- Permiso de lectura nuevo `equipos:ver`, fail-closed.

**Non-Goals:**
- NO se crea una tabla `EquipoDocente` (OQ-1: equipo = proyección derivada).
- NO se modela multi-responsable por asignación (OQ-2: tabla puente fuera de scope; responsable único por lote).
- NO se toca el CRUD unitario de `/asignaciones` ni la spec `asignaciones`.
- NO se implementa el autocompletado de UI (RN-30 es soporte de búsqueda; el endpoint de búsqueda de usuarios ya existe en C-07 / se delega al frontend C-23).
- NO se importa/exporta a Moodle aquí.
- NO se agregan formatos de export distintos a CSV.

## Decisions

### D1 — El equipo es una proyección derivada de `Asignacion`, sin tabla nueva (resuelve OQ-1)
La tripleta `(materia_id, carrera_id, cohorte_id)` identifica un equipo. Todas las operaciones consultan/mutan `Asignacion` filtrando por esa tripleta + tenant.
**Por qué**: una sola fuente de verdad, ninguna migración de schema, cero riesgo de desincronización entre "el equipo" y "sus asignaciones". El roadmap pide una sola migración por change; aquí no hace falta ninguna de dominio.
**Alternativa descartada**: materializar `EquipoDocente` con metadatos propios. Se descarta hasta que negocio pida atributos de equipo (nombre, notas, estado). Si eso ocurre, será otro change con su migración.

### D2 — Router separado `/api/v1/equipos`, no extender `/asignaciones`
Las operaciones de equipo viven en `backend/app/api/v1/routers/equipos.py`.
**Por qué**: `/asignaciones` es CRUD unitario; mezclar bulk/clonado/export lo infla y rompe el límite de ≤500 LOC. Separar respeta el límite y mantiene los routers cohesivos.
**Alternativa descartada**: subrutas dentro de `/asignaciones` (`/asignaciones/masiva`, etc.). Se descarta por cohesión y por el límite de LOC.

### D3 — Capa de servicio dedicada `EquipoService`, repos reutilizados/extendidos
`backend/app/services/equipo_service.py` orquesta agrupación, masiva, clonado, vigencia general y export. Reutiliza `AsignacionRepository` y `UsuarioRepository` (C-07), agregando a `AsignacionRepository` métodos de consulta por tripleta y operaciones bulk (`list_by_equipo`, `bulk_add`, `bulk_update_vigencia`).
**Por qué**: Clean Architecture — nada de lógica en el router, nada de DB directa en el service. Extender el repo existente mantiene el scope de tenant centralizado (heredado de `TenantScopedRepository`).
**Alternativa descartada**: repo nuevo `EquipoRepository`. Innecesario: opera sobre la misma tabla `Asignacion`; un repo nuevo duplicaría el scope de tenant.

### D4 — Nuevo permiso de lectura `equipos:ver`; mutaciones siguen con `equipos:asignar`
Lecturas (mis-equipos, consulta de equipo, export) → `equipos:ver`. Mutaciones (masiva, clonar, vigencia general) → `equipos:asignar` (ya existe).
**Por qué**: separar lectura de escritura permite que un docente vea sus equipos sin poder mutarlos (fail-closed por defecto). RBAC fino `modulo:accion`.
**Alternativa descartada**: reutilizar `equipos:asignar` para todo. Se descarta porque obligaría a dar permiso de mutación a quien solo necesita ver, violando el principio de mínimo privilegio.
**Nota de seguridad (regla dura #8/#14)**: en mis-equipos el `usuario_id` se toma del JWT (`current_user.user_id`), nunca de la URL/body. El permiso `equipos:ver` autoriza la acción; el filtro por identidad propia lo impone el service.

### D5 — Asignación masiva atómica en una transacción
El service valida TODOS los `usuario_id`, contexto y `responsable_id` (mismo tenant) ANTES de persistir; persiste el lote en una sola transacción. Si algo falla → rollback, ninguna asignación creada.
**Por qué**: HU-18 espera "todas o ninguna"; un lote a medio crear deja el equipo inconsistente. Reusa las excepciones de C-07 (`UsuarioNoEncontrado`, `ReferenciaInvalida`) mapeadas a 422.
**Trade-off**: el commit único difiere del `add()` por-registro de `TenantScopedRepository` (que commitea cada vez). Por eso se agrega `bulk_add` que hace `add_all` + un único `commit`.

### D6 — Clonación no-destructiva con skip de duplicados (resuelve OQ-3)
Se leen las asignaciones vigentes del origen, se filtran las que ya existirían en el destino (mismo `usuario_id` + `rol` + contexto destino, no soft-deleted) y se crean solo las nuevas con la vigencia del destino. Devuelve `ResumenClonacion(clonadas, omitidas)`.
**Por qué**: re-clonar no debe duplicar; un coordinador puede ejecutar la operación dos veces sin romper el equipo (idempotencia práctica).
**Alternativa descartada**: clonar siempre (duplica) o upsert por fechas. Se descarta: duplicar corrompe; upsert sobre fechas es ambiguo y no lo pide negocio.

### D7 — Responsable único por lote en la masiva (resuelve OQ-2)
La asignación masiva acepta un `responsable_id` opcional aplicado a todas las asignaciones del lote.
**Por qué**: el modelo `Asignacion.responsable_id` es un self-FK único; cubre el caso principal de FL-03. Multi-responsable por asignación exigiría tabla puente → fuera de C-08.

### D8 — Export CSV en memoria, streaming de respuesta
El service produce el CSV (filas: docente, rol, materia, carrera, cohorte, comisiones, vigencia, estado) y el router lo devuelve como `StreamingResponse`/`Response` con `Content-Disposition: attachment`. `estado_vigencia` se deriva con el helper puro `app.models.vigencia.estado_vigencia` (reusa C-07).
**Por qué**: CSV es lo que pide F4.7; sin dependencias nuevas (`csv` stdlib). Equipos chicos → no se necesita streaming de DB.

### D9 — Auditoría de operaciones en bloque vía `AuditRepository` (C-05)
Masiva, clonar y vigencia general emiten eventos `EQUIPOS_ASIGNACION_MASIVA`, `EQUIPOS_CLONAR`, `EQUIPOS_VIGENCIA_GENERAL` con actor (JWT), tenant, contexto del equipo y cantidades. Lecturas no se auditan (consultas, no cambios de estado).
**Por qué**: el producto es *trace* — toda mutación audita. Reusa el patrón de `calificaciones` (inyecta `audit_repo` en el service).
**Catálogo**: las tres claves se agregan al catálogo de acciones de auditoría existente (seed). Si el catálogo es una tabla seedeada, esto entra en la migración del catálogo de permisos/auditoría (ver Migration Plan); si es un enum estático, se agrega al enum.

### D10 — Schemas Pydantic v2 con `extra='forbid'`
`backend/app/schemas/equipo.py`: `MisEquiposItem`, `EquipoQuery`, `AsignacionMasivaRequest`, `ClonarEquipoRequest`, `VigenciaGeneralRequest`, `ResumenLote`, `ResumenClonacion`. Todos `model_config = ConfigDict(extra='forbid')`. Reusan `AsignacionRead`/`estado_vigencia` donde aplique.

## Risks / Trade-offs

- **[Falsa premisa OQ-1: negocio sí quería tabla `EquipoDocente`]** → Mitigación: las tres OQ están explícitas en el proposal; si se confirma lo contrario antes de apply, se agrega la tabla y su migración como ajuste acotado. El diseño derivado no bloquea esa evolución.
- **[Clonación masiva costosa si el equipo es grande]** → Mitigación: una sola transacción con `add_all`; equipos docentes son del orden de decenas, no miles. Si crece, paginar/batch en un change futuro.
- **[Permiso `equipos:ver` ausente en tenants ya seedeados]** → Mitigación: el seed/migración del catálogo agrega `equipos:ver` y, si corresponde por política del proyecto, lo asocia a los roles que ya tienen `equipos:asignar` + a los roles docentes (PROFESOR/TUTOR/NEXO/COORDINADOR) para mis-equipos. Fail-closed: sin el permiso, 403 (comportamiento seguro por defecto).
- **[Operación bulk salta el commit por-registro de `TenantScopedRepository`]** → Mitigación: `bulk_add`/`bulk_update_vigencia` controlan la transacción explícitamente y siguen forzando `tenant_id` desde el scope del repo (no del input).
- **[Export filtra mal y filtra PII de otro tenant]** → Mitigación: el export pasa por `AsignacionRepository` con scope de tenant; tests con DB real cubren el cruce de tenants. El CSV no incluye PII sensible cifrada (DNI/CBU): solo nombre, rol y contexto académico.

## Migration Plan

1. **Catálogo RBAC**: agregar el permiso `equipos:ver`. Si el catálogo de permisos vive en tabla seedeada (C-04), se agrega en la migración única de este change (alta del permiso + asociación a roles según política). Si es estático, se agrega al catálogo en código.
2. **Catálogo de auditoría**: agregar las claves `EQUIPOS_ASIGNACION_MASIVA`, `EQUIPOS_CLONAR`, `EQUIPOS_VIGENCIA_GENERAL` (tabla seedeada o enum, según implementación de C-05).
3. **Sin migración de schema de dominio** (D1): no hay tablas/columnas nuevas. La única migración Alembic posible es la del catálogo (permiso/auditoría) — una sola, conforme a la regla dura.
4. **Despliegue**: el router `/api/v1/equipos` se monta en el agregador de routers de la API v1.
5. **Rollback**: revertir la migración del catálogo (baja del permiso/acciones) y desmontar el router. Sin datos de dominio creados por el schema → rollback limpio. Las asignaciones creadas vía masiva/clonado son datos de negocio normales (soft-delete si hay que retirarlas).

## Decisiones resueltas (ex Open Questions)

> Las 4 preguntas abiertas fueron **resueltas por el usuario** y están CERRADAS. El apply implementa estas decisiones directamente.

| ID | Decisión | Racional |
|----|----------|----------|
| **OQ-1** — ¿Entidad materializada o derivada? | **RESUELTA: vista derivada, sin tabla nueva.** Negocio no requiere metadatos propios de equipo. Sin migración de schema de dominio. | Única fuente de verdad en `Asignacion`; sin riesgo de desincronización. Ver D1. |
| **OQ-2** — Multi-responsable en la masiva | **RESUELTA: responsable único por lote.** Multi-responsable por asignación requiere tabla puente → fuera de C-08. | El modelo `Asignacion.responsable_id` es self-FK único. Ver D7. |
| **OQ-3** — Idempotencia de clonación | **RESUELTA: clonación no-destructiva con skip de duplicados.** Re-clonar omite existentes y reporta `(clonadas, omitidas)`. | Evita duplicados si el coordinador ejecuta la operación más de una vez. Ver D6. |
| **OQ-4** — Asociación de `equipos:ver` en el seed | **RESUELTA: roles de gestión (ADMIN, COORDINADOR, FINANZAS) para consulta general; roles docentes (PROFESOR, TUTOR, NEXO) para la vista "mis-equipos".** La asociación entra en la migración del catálogo RBAC. | Mínimo privilegio: docentes ven sus propios equipos; coordinadores ven cualquier equipo del tenant. |
