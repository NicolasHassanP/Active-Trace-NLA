## Context

C-12 cierra el camino crítico del producto (`C-01 → … → C-11 → C-12`). C-11 (analisis-atrasados-reportes, archivado 2026-06-04) ya identifica alumnos atrasados; C-12 agrega el canal de comunicación saliente: encolar, previsualizar, aprobar y despachar emails de forma asíncrona.

Restricciones duras del proyecto (de `CLAUDE.md`, no negociables):
- Clean Architecture unidireccional: Routers → Services → Repositories → Models.
- Multi-tenancy row-level (`tenant_id` en cada tabla; repos filtran por tenant).
- RBAC fino `modulo:accion`, fail-closed.
- PII cifrada AES-256 vía `app.core.security.crypto.EncryptedString` (mismo patrón que `Usuario` en C-07).
- Soft delete siempre; ≤500 LOC por archivo; UNA migración Alembic.
- Tests con DB real (sin mocks de DB). Strict TDD en apply.

Patrones existentes a reusar:
- `EncryptedString` + `__repr__` que nunca expone PII → `backend/app/models/usuario.py`.
- Repo tenant-scoped → `backend/app/repositories/base.py` (`TenantScopedRepository`).
- Service con audit_repo + identidad desde `current_user` → `backend/app/services/calificacion_service.py`.
- Router con `require_permission(...)` y factory de service → `backend/app/api/v1/routers/calificaciones.py`.
- Enum `audit_action` con ADD VALUE idempotente (DO/EXCEPTION) → migración 004 y 008.
- Placeholder de worker a reemplazar → `backend/app/workers/main.py`.

## Goals / Non-Goals

**Goals**
- Modelo `Comunicacion` con `destinatario` cifrado, `lote_id`, máquina de estados RN-15 (con `Error` terminal).
- Tabla `tenant_config` (clave/valor) para settings por tenant, alojando `aprobacion_comunicacion_requerida`.
- Preview obligatorio con render de plantilla (RN-16) antes de encolar; falla fuerte ante variable sin resolver.
- Encolado masivo por lote (F3.2); el PROFESOR solo a destinatarios de sus comisiones (scope `propio` contra `Asignacion`).
- Aprobación humana configurable por tenant (vía `tenant_config`), a nivel lote e individual (RN-17, F3.3).
- Worker asíncrono (polling sobre la tabla) que transiciona `Pendiente → Enviando → Enviado/Error` respetando la aprobación.
- Envío físico aislado tras `EmailSender` (Protocol) con un `TestSender`.
- Auditoría `COMUNICACION_ENVIAR`.

**Non-Goals**
- Integración real con un proveedor SMTP / servicio de email externo. En C-12 el envío se aísla tras `EmailSender` con un `TestSender`; el proveedor real es un change futuro (OQ-3).
- Cola basada en broker (Redis/ARQ/Celery) u orquestación N8N. En C-12 la cola es la tabla (polling). Migrar a broker es un change futuro (OQ-1).
- Reintentos automáticos / backoff: `Error` es terminal en C-12; re-encolar es manual (OQ-5).
- Mensajería interna entre usuarios / comunicación entre docentes (F3.4 / FL-10) — fuera de scope, es otro módulo (OQ-7).
- Frontend (panel de comunicaciones) — corresponde a un change de frontend.

## Decisions

### D1 — Modelo `Comunicacion` sobre `TenantScopedBase`, `destinatario` cifrado
Tabla `comunicacion` con: `id`, `tenant_id`, `enviado_por` (FK `usuario.id`), `materia_id` (FK `materia.id`), `destinatario` (`EncryptedString`, AES-256-GCM), `asunto` (texto), `cuerpo` (texto enriquecido), `estado` (enum `comunicacion_estado`), `lote_id` (UUID, indexado), `enviado_at` (TIMESTAMPTZ nullable), `error_detalle` (texto nullable) + base soft-delete/timestamps. `__repr__` NUNCA expone `destinatario` en texto plano (igual que `Usuario`).
**Alternativa descartada**: blind index sobre el destinatario (como `email_hash` en `Usuario`). No hace falta: no se busca ni se impone unicidad por destinatario en este módulo. Se omite para no exponer un hash determinístico innecesario.

### D2 — Máquina de estados como función pura (`comunicacion_estados.py`)
Enum `ComunicacionEstado = {Pendiente, Enviando, Enviado, Error, Cancelado}`. Transiciones válidas (RN-15):
```
Pendiente → Enviando        (worker toma el mensaje; o aprobación libera al worker)
Pendiente → Cancelado       (cancelación antes del despacho)
Enviando  → Enviado         (despacho OK)
Enviando  → Error           (fallo de despacho)
```
Una función pura `puede_transicionar(actual, destino) -> bool` y `transicionar(com, destino)` que lanza `TransicionInvalidaError` (excepción de dominio) si la transición no está permitida. Pura = fácil de testear por triangulación, sin DB.

**`Error` es estado TERMINAL (decisión cerrada OQ-5)**: no hay transición de salida desde `Error` (ni reintento automático). Reintentar significa una re-acción manual del usuario (re-encolar genera un nuevo registro/lote), o un change futuro. `Enviado` y `Cancelado` también son terminales. Esto se codifica en el mapa de transiciones: `Error`, `Enviado` y `Cancelado` no tienen destinos válidos.
**Alternativa descartada**: librería de state machine (transitions). Overkill para 5 estados y 4 aristas; agrega dependencia.

### D3 — Envío físico aislado tras `EmailSender` (Protocol) + `TestSender`
**Decisión cerrada (OQ-3)**: el worker no habla SMTP directamente. Depende de una interfaz `EmailSender` (typing.Protocol) con método `async send(destinatario: str, asunto: str, cuerpo: str) -> None`. En C-12 se implementa un `TestSender`/`FakeSender` que registra el envío (in-memory) sin SMTP real y permite forzar fallo para testear la rama `→ Error`. El proveedor real (SMTP / servicio transaccional / N8N) queda fuera de scope — es trabajo de un change futuro (Non-Goal de C-12). Esto mantiene el worker testeable end-to-end con DB real y desacopla ADR-003.

### D4 — Worker asíncrono en `backend/app/workers/` (polling sobre la tabla)
**Decisión cerrada (OQ-1)**: la cola es la propia tabla `comunicacion`. El worker hace **polling sobre la tabla** de los `Pendiente` aprobados/elegibles y transiciona estados. SIN broker (Redis/ARQ/Celery) ni N8N en C-12.

`comunicacion_worker.py`: loop que (1) consulta `Comunicacion` en estado `Pendiente` que estén habilitadas para despacho (aprobadas o sin requerir aprobación), (2) transiciona a `Enviando` de forma atómica (`UPDATE ... WHERE estado='Pendiente'`), (3) invoca `EmailSender`, (4) transiciona a `Enviado` o `Error` con `enviado_at`/`error_detalle`. Reemplaza el placeholder de `main.py`.

**Diseñado para no acoplar el dominio al transporte**: la lógica de estados (D2) y el envío físico (D3) son independientes del mecanismo de polling. Migrar a un broker dedicado en un change futuro NO debe tocar la máquina de estados ni el `EmailSender`; solo el loop del worker. El broker es Non-Goal de C-12.

### D5 — Plantillas con sustitución de variables (`comunicacion_plantilla.py`) — falla fuerte
**Decisión cerrada (OQ-4)**: ante una variable de plantilla faltante o sin resolver, el sistema **falla fuerte** — NO se renderiza parcial, NO se encola y NO se envía una comunicación con marcadores sin resolver.

Función pura `render(plantilla: str, variables: dict) -> str` que sustituye marcadores `{nombre}`, `{materia}`, etc. Si la plantilla contiene un marcador para el que no se provee valor, `render` lanza `VariablePlantillaFaltanteError` (excepción de dominio) en lugar de dejar el marcador literal o sustituir por vacío. Usada por el preview (RN-16) y por el encolado para materializar asunto/cuerpo por destinatario. **La validación de plantilla ocurre en el preview** (RN-16): el preview es el punto donde el usuario ve si faltan variables; el encolado vuelve a renderizar por destinatario y también falla fuerte si algo no resuelve, garantizando que nunca se persista un mensaje con marcadores abiertos.

### D6 — Aprobación configurable por tenant vía tabla `tenant_config`
**Decisión cerrada (OQ-2)**: el flag `aprobacion_comunicacion_requerida` vive en una **nueva tabla `tenant_config`** de settings por tenant, creada en la MISMA migración 009. Patrón elegido: **clave/valor tipado** (un row por flag), extensible a futuros flags sin migrar el schema por cada uno.

Esquema mínimo de `tenant_config`:
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | UUID PK | identidad interna |
| `tenant_id` | UUID FK `tenants.id`, NOT NULL, indexado | scope de tenant (regla dura 9) |
| `clave` | VARCHAR NOT NULL | nombre del setting, p. ej. `aprobacion_comunicacion_requerida` |
| `valor` | VARCHAR NOT NULL | valor serializado como texto (`"true"`/`"false"`) |
| + base | — | timestamps + soft delete vía `TenantScopedBase` |

Restricción de unicidad: `UNIQUE (tenant_id, clave)` (entre filas vivas) — un valor por clave por tenant.

**Por qué clave/valor y no columna en `tenants`**: la KB pide "configurable por tenant" y anticipa más flags por tenant a futuro. Una tabla de settings evita engordar `tenants` con una columna por flag y centraliza la configuración. Se elige clave/valor texto (no JSONB) por simplicidad y consistencia con el resto del modelo relacional; la lectura tipa el valor en el repositorio (`get_bool(tenant_id, clave, default=False)`).

**Cómo se lee el flag**: un `TenantConfigRepository.get_bool("aprobacion_comunicacion_requerida", default=...)` tenant-scoped. El `ComunicacionService` lo consulta al encolar y el worker al seleccionar mensajes elegibles. Si no existe fila para el tenant, se aplica el `default`. La migración 009 NO siembra valores; cada tenant configura su flag explícitamente. El worker solo despacha mensajes marcados como elegibles, de modo que el efecto del flag es determinista en cada operación de encolado.

El flujo: si el flag está activo, el encolado masivo deja los mensajes en `Pendiente` y el worker los ignora hasta que un usuario con `comunicacion:aprobar` apruebe el lote o el destinatario individual. Aprobar = habilitar para despacho; cancelar = `→ Cancelado`. Si el flag está inactivo, los mensajes son elegibles para el worker directamente.

### D6b — Scope `propio` del PROFESOR validado contra `Asignacion` (C-07)
**Decisión cerrada (OQ-6)**: el seed RBAC da a PROFESOR `comunicacion:enviar` con scope `propio`. "Propio" significa que el PROFESOR solo puede comunicar a destinatarios de **sus** comisiones. Al encolar, el `ComunicacionService` valida que cada destinatario pertenezca a una comisión donde el PROFESOR tiene `Asignacion` vigente (modelo de C-07). Si un destinatario cae fuera de su scope, el encolado se rechaza (no se crea el lote parcial). Roles con scope más amplio (COORDINADOR/ADMIN según el seed) no aplican esta restricción.

### D7 — Auditoría `COMUNICACION_ENVIAR`
Se agrega `COMUNICACION_ENVIAR` al enum `audit_action` (ADD VALUE idempotente, patrón de migración 004/008) y al enum Python `AuditAction` en `app/models/audit.py`. Se registra un evento de auditoría al encolar (acción del docente) y al aprobar (acción del aprobador), vía `AuditRepository`, igual que `calificacion_service`.

### D8 — Migración `009`
`revision="009"`, `down_revision="008"` (008 es la última: C-10; C-11 fue capa de análisis sin migración). En una sola migración para todo el schema del change crea:
- enum `comunicacion_estado`;
- tabla `comunicacion` con índices por (`tenant_id`, `estado`) y `lote_id`;
- tabla **`tenant_config`** (esquema de D6) con `UNIQUE (tenant_id, clave)`;
- `ALTER TYPE audit_action ADD VALUE 'COMUNICACION_ENVIAR'` idempotente (patrón DO/EXCEPTION de las migraciones 004/008).

Los permisos `comunicacion:enviar` / `comunicacion:aprobar` ya existen en el seed RBAC (migración 003) — NO se re-crean.

## Risks / Trade-offs

- **[Polling de la tabla como cola puede no escalar]** → baseline simple y testeable (decisión OQ-1); la migración a un broker es un change futuro (Non-Goal). El diseño aísla el worker tras `EmailSender` y la máquina de estados es independiente del transporte, así que cambiar el transporte no toca el dominio.
- **[TestSender no envía emails reales]** → explícito como Non-Goal (OQ-3); el flujo de estados y la auditoría sí se validan end-to-end con DB real. El proveedor real es un change futuro.
- **[Race condition: dos workers toman el mismo `Pendiente`]** → mitigación: la transición `Pendiente → Enviando` es atómica (UPDATE condicional `WHERE estado='Pendiente'`); un solo worker en baseline. Surface en apply.
- **[Fallo de envío sin reintento automático]** → `Error` es terminal (OQ-5); el reintento es una re-acción manual (re-encolar). Riesgo aceptado para el MVP; los `Error` quedan visibles con `error_detalle` para acción humana.
- **[`tenant_config` clave/valor texto exige tipado en lectura]** → mitigado por `TenantConfigRepository.get_bool(...)` que centraliza el casteo; el costo es bajo frente a la flexibilidad de no migrar por cada flag nuevo.

## Migration Plan

1. Crear migración `009` (enum `comunicacion_estado` + tabla `comunicacion` + tabla `tenant_config` + extend `audit_action`). `alembic upgrade head`.
2. Rollback: `downgrade` elimina las tablas `comunicacion` y `tenant_config` y el enum `comunicacion_estado`. El ADD VALUE en `audit_action` NO se revierte (PostgreSQL no soporta DROP VALUE de un enum de forma simple); es aditivo e idempotente, sin impacto.
3. El worker se despliega como proceso separado (ya hay `app/workers/main.py` como entrypoint).

## Decisiones resueltas (ex Open Questions)

> Las 7 preguntas abiertas que este change elevó fueron **resueltas por el usuario** y están CERRADAS. Se registran aquí con la opción elegida y su racional; el apply implementa estas decisiones (el checkpoint de gobernanza ALTO de la tarea 0.1 ya está cubierto por estas resoluciones).

| ID | Decisión | Racional |
|----|----------|----------|
| **OQ-1** — tecnología de cola | **RESUELTA: polling sobre la tabla.** La tabla `comunicacion` ES la cola; el worker hace polling de los `Pendiente` aprobados y transiciona estados. SIN broker/Redis/N8N. | Simple, sin infra extra, testeable con DB real. El diseño aísla el dominio del transporte (D2/D3/D4) para que migrar a broker después no toque la máquina de estados ni `EmailSender`. Ver D4. |
| **OQ-2** — flag de aprobación por tenant | **RESUELTA: nueva tabla `tenant_config`** (clave/valor tipado) que aloja `aprobacion_comunicacion_requerida`, creada en la migración 009. Extensible a futuros flags. | Evita engordar `tenants` con una columna por flag; centraliza settings por tenant. Esquema y lectura en D6. |
| **OQ-3** — proveedor de email | **RESUELTA: interfaz `EmailSender` (Protocol) + `TestSender`/`FakeSender`** que registra el envío sin SMTP real. El proveedor real es Non-Goal de C-12 (change futuro). | Mantiene el worker testeable end-to-end y desacopla ADR-003. Ver D3. |
| **OQ-4** — variable de plantilla faltante | **RESUELTA: fallar fuerte.** No se renderiza parcial, no se encola ni se envía una comunicación con variables sin resolver. La validación ocurre en el preview (RN-16). | Evita despachar mensajes con marcadores abiertos al alumno. Ver D5. |
| **OQ-5** — error / reintentos | **RESUELTA: `Error` es estado TERMINAL.** Sin reintentos automáticos en C-12; reintentar = re-encolar manual (o change futuro). | Mantiene el worker simple; los `Error` quedan visibles con `error_detalle`. Ver D2. |
| **OQ-6** — scope `propio` del PROFESOR | **RESUELTA: validar contra `Asignacion` (C-07).** Al encolar, el PROFESOR solo puede comunicar a destinatarios de SUS comisiones (donde tiene asignación vigente). | Concreta el scope `propio` del seed RBAC. Ver D6b. |
| **OQ-7** — mensajería interna (F3.4/FL-10) | **RESUELTA: Non-Goal de C-12.** La comunicación entre docentes / mensajería interna queda explícitamente fuera de scope. | C-12 cubre comunicación saliente hacia alumnos (FL-02/FL-04). Registrado en Non-Goals del proposal. |
