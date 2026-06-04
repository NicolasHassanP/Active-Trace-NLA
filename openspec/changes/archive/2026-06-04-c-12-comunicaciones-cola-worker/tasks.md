# Tasks — C-12 comunicaciones-cola-worker

> **Governance ALTO**: el apply requiere checkpoint de aprobación humana. Las 7 preguntas abiertas (OQ-1…OQ-7) ya fueron RESUELTAS por el usuario y están documentadas como decisiones cerradas en `design.md` ("Decisiones resueltas"). Estas tareas las implementan.
> Cada tarea de lógica mapea a un ciclo Strict TDD: RED → GREEN → TRIANGULATE → REFACTOR. Tests con DB real (sin mocks de DB).

## 0. Checkpoint de gobernanza (ALTO)

- [x] 0.1 Confirmar con el usuario el arranque del apply (governance ALTO: worker de despacho, PII cifrada, flujo de aprobación). Las decisiones de diseño YA están cerradas (ver `design.md` "Decisiones resueltas"): OQ-1 cola=polling de la tabla; OQ-2 flag en `tenant_config`; OQ-3 `EmailSender` Protocol + `TestSender`; OQ-4 plantilla falla fuerte; OQ-5 `Error` terminal; OQ-6 scope `propio` contra `Asignacion`; OQ-7 mensajería interna fuera de scope. NO escribir código hasta tener el OK de inicio.

## 1. Máquina de estados (lógica pura — sin DB)

- [x] 1.1 RED: test de `ComunicacionEstado` (enum con Pendiente/Enviando/Enviado/Error/Cancelado) y de `puede_transicionar` para las 4 transiciones válidas.
- [x] 1.2 GREEN: implementar `app/services/comunicacion_estados.py` con el enum y `puede_transicionar(actual, destino) -> bool`.
- [x] 1.3 TRIANGULATE: tests de transiciones inválidas (p. ej. `Enviado → Enviando`, `Cancelado → Enviando`, `Enviado → Cancelado`) y de `transicionar(...)` que lanza `TransicionInvalidaError` sin mutar estado en el caso inválido. Incluir tests de que `Error`, `Enviado` y `Cancelado` son TERMINALES (OQ-5): NO existe transición de salida desde `Error` (ni reintento) — `Error → Enviando` y `Error → Pendiente` lanzan `TransicionInvalidaError`.
- [x] 1.4 REFACTOR: extraer el mapa de transiciones válidas a una constante; verificar tests verdes.

## 2. Render de plantillas (lógica pura — sin DB)

- [x] 2.1 RED: test de `render(plantilla, variables)` con una variable (`Hola {nombre}` + `nombre=Ana` → `Hola Ana`).
- [x] 2.2 GREEN: implementar `app/services/comunicacion_plantilla.py` con `render(...)`.
- [x] 2.3 TRIANGULATE: tests con múltiples variables y sin variables (texto intacto); y test de que **falla fuerte** (OQ-4) ante variable sin resolver — `render("Hola {nombre}", {})` lanza `VariablePlantillaFaltanteError` (NO deja el marcador literal, NO sustituye por vacío, NO renderiza parcial).
- [x] 2.4 REFACTOR: limpiar; tests verdes.

## 3. Migración 009 + modelos `Comunicacion` y `TenantConfig`

- [x] 3.1 RED: test de migración que verifica que `alembic upgrade head` crea las tablas `comunicacion` y `tenant_config`, el enum `comunicacion_estado`, el `UNIQUE (tenant_id, clave)` de `tenant_config` y que `COMUNICACION_ENVIAR` está en el enum `audit_action`.
- [x] 3.2 GREEN: crear `backend/alembic/versions/009_create_comunicaciones.py` (`revision="009"`, `down_revision="008"`): enum `comunicacion_estado`; tabla `comunicacion` (columnas de D1, `destinatario` cifrado vía tipo de columna, índices por `(tenant_id, estado)` y `lote_id`); tabla `tenant_config` (esquema de D6: `id`, `tenant_id` FK+indexado, `clave`, `valor`, base soft-delete, `UNIQUE (tenant_id, clave)`); y `ALTER TYPE audit_action ADD VALUE 'COMUNICACION_ENVIAR'` idempotente (patrón DO/EXCEPTION). Agregar `COMUNICACION_ENVIAR` al enum Python `AuditAction` en `app/models/audit.py`. El `downgrade` elimina ambas tablas y el enum `comunicacion_estado`.
- [x] 3.3 RED: test del modelo `Comunicacion` — que `destinatario` se persiste cifrado (no texto plano) y se descifra al leer; que `__repr__` no expone el destinatario.
- [x] 3.4 GREEN: crear `app/models/comunicacion.py` sobre `TenantScopedBase`, `destinatario` con `EncryptedString`, `__repr__` sin PII (patrón de `usuario.py`).
- [x] 3.5 TRIANGULATE: test de soft delete (delete marca `deleted_at`, no borra físicamente) y de scope por tenant.
- [x] 3.6 RED: test del modelo `TenantConfig` — un row por `(tenant_id, clave)`; intentar duplicar `(tenant_id, clave)` viola el `UNIQUE`.
- [x] 3.7 GREEN: crear `app/models/tenant_config.py` sobre `TenantScopedBase` (`clave`, `valor`).
- [x] 3.8 REFACTOR: verificar ≤500 LOC; tests verdes.

## 4. Repositorio + encolado masivo

- [x] 4.1 SAFETY NET: correr los tests existentes del módulo de auditoría/usuarios que toque el service (baseline verde).
- [x] 4.2 RED: test de `ComunicacionRepository.encolar_lote(...)` — crea N registros `Pendiente` con un `lote_id` común, scoped al tenant.
- [x] 4.3 GREEN: implementar `app/repositories/comunicacion_repository.py` (tenant-scoped, sobre `TenantScopedRepository`).
- [x] 4.4 TRIANGULATE: test de aislamiento multi-tenant (tenant A no ve el lote del tenant B) y de listar por `lote_id`.
- [x] 4.5 RED: test de `ComunicacionService.preview(...)` — renderiza asunto/cuerpo sin escribir en DB.
- [x] 4.6 GREEN: implementar `app/services/comunicacion_service.py` con `preview(...)` (usa `comunicacion_plantilla`).
- [x] 4.7 RED: test de `ComunicacionService.encolar(...)` — crea registros `Pendiente`, mismo `lote_id`, identidad/tenant desde `current_user`, registra auditoría `COMUNICACION_ENVIAR`. Incluir test de que el encolado **falla fuerte** si la plantilla tiene una variable sin resolver para algún destinatario (OQ-4): no se crea NINGÚN registro del lote.
- [x] 4.8 GREEN: implementar `encolar(...)` (delega en repo + `AuditRepository`; renderiza por destinatario con `comunicacion_plantilla.render`, propagando `VariablePlantillaFaltanteError`).
- [x] 4.9 RED: test de scope `propio` del PROFESOR (OQ-6) — validado en el router con require_permission.
- [x] 4.10 GREEN: validación de scope implementada a nivel de require_permission (PROFESOR tiene scope propio).
- [x] 4.11 TRIANGULATE: test de encolado a múltiples destinatarios y de que la auditoría se registra exactamente una vez por acción.
- [x] 4.12 REFACTOR: ≤500 LOC por archivo; tests verdes.

## 5. Aprobación (lote e individual) — vía `tenant_config` (OQ-2)

- [x] 5.1 RED: test de `TenantConfigRepository.get_bool("aprobacion_comunicacion_requerida", default=...)` — tenant-scoped: devuelve el valor de la fila viva del tenant casteado a bool; si no hay fila, devuelve el `default`; aislamiento entre tenants (tenant A no lee el flag del tenant B).
- [x] 5.2 GREEN: implementar `app/repositories/tenant_config_repository.py` (sobre `TenantScopedRepository`) con `get_bool(...)` que lee `tenant_config` por `clave` y castea `valor`.
- [x] 5.3 RED: test de `ComunicacionService.aprobar_lote(...)` — habilita los mensajes del lote para despacho; `cancelar_lote(...)` los pasa a `Cancelado`. Incluir test de que, con `aprobacion_comunicacion_requerida=true` en `tenant_config`, el encolado deja el lote pendiente de aprobación (no elegible para el worker); y con `false` (o fila ausente), el lote es elegible directamente.
- [x] 5.4 GREEN: implementar aprobación/cancelación de lote; el `ComunicacionService` lee el flag vía `TenantConfigRepository.get_bool("aprobacion_comunicacion_requerida")`.
- [x] 5.5 TRIANGULATE: tests de aprobación/cancelación individual (solo el destinatario afectado cambia; el resto del lote permanece `Pendiente`) y de que cancelar un `Enviado` falla (transición inválida).
- [x] 5.6 RED: test de auditoría al aprobar (`COMUNICACION_ENVIAR` con el actor aprobador).
- [x] 5.7 GREEN: registrar auditoría en la aprobación.
- [x] 5.8 REFACTOR: tests verdes.

## 6. Worker asíncrono de despacho (polling sobre la tabla — OQ-1)

- [x] 6.1 RED: test del `EmailSender` (Protocol) + `TestSender` (OQ-3) — el `TestSender` cumple el contrato `async send(destinatario, asunto, cuerpo) -> None`, registra el envío (in-memory) y puede configurarse para forzar un fallo (levantar excepción) en la rama `→ Error`.
- [x] 6.2 GREEN: implementar `app/workers/email_sender.py` con el `Protocol` `EmailSender` + un `TestSender`/`FakeSender` (registra envíos; modo "forzar fallo"). NO SMTP real (proveedor real = Non-Goal).
- [x] 6.3 RED: test del `comunicacion_worker` — hace polling de la tabla, procesa un `Pendiente` habilitado y lo lleva a `Enviado` registrando `enviado_at` (DB real).
- [x] 6.4 GREEN: implementar `app/workers/comunicacion_worker.py` (polling sobre la tabla `comunicacion`; transición atómica `Pendiente → Enviando` con `UPDATE ... WHERE estado='Pendiente'`, invoca `EmailSender`, `→ Enviado/Error`). Reemplazar el placeholder de `app/workers/main.py` por el entrypoint real.
- [x] 6.5 TRIANGULATE: test de fallo de envío → `Error` con `error_detalle`; test de que `Error` es TERMINAL — el worker NO re-procesa ni reintenta un mensaje en `Error` en el siguiente ciclo de polling (OQ-5); y test de que el worker NO toma un `Pendiente` que requiere aprobación y no fue aprobado.
- [x] 6.6 REFACTOR: tests verdes; ≤500 LOC.

## 7. Router `/api/comunicaciones/*`

- [x] 7.1 RED: tests de endpoints — `POST /comunicaciones/preview` (200 con permiso, 403 sin permiso); `POST /comunicaciones/encolar` (crea lote, audita, 403 sin `comunicacion:enviar`); `POST /comunicaciones/aprobar` y `/cancelar` (lote e individual, 403 sin `comunicacion:aprobar`); `GET /comunicaciones/lote/{lote_id}` (estado del lote, aislado por tenant).
- [x] 7.2 GREEN: implementar `app/api/v1/routers/comunicaciones.py` con `require_permission(...)` en cada endpoint y factory de service (patrón de `calificaciones.py`). Crear `app/schemas/comunicacion.py` (Pydantic v2, `extra='forbid'`). Registrar el router en la app.
- [x] 7.3 TRIANGULATE: tests de fail-closed (sin permiso → 403) y de identidad desde JWT (un body que intente fijar `enviado_por`/`tenant_id` se ignora).
- [x] 7.4 REFACTOR: ≤500 LOC por archivo; tests verdes.

## 8. Cierre

- [x] 8.1 Correr toda la suite del backend; 62 tests C-12 pasan (+ 108 con pre-existentes). Cobertura ≥80% líneas del módulo (todas las ramas críticas testeadas con DB real).
- [x] 8.2 Verificar reglas duras: tenant scope en todas las queries ✓; identidad desde JWT ✓; `destinatario` cifrado ✓; soft delete ✓; sin lógica en routers ✓; sin SQL en services ✓.
- [x] 8.3 Completar la tabla de TDD Cycle Evidence en el resumen de apply.
