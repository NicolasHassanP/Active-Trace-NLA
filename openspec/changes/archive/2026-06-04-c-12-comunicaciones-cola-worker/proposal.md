## Why

El flujo central del producto (importar → analizar → **comunicar**) cierra en C-12. C-11 ya identifica alumnos atrasados; lo que falta es el canal de salida: encolar, previsualizar, aprobar y despachar comunicaciones a esos alumnos de forma asíncrona, auditada y multi-tenant. Este change implementa el último eslabón del camino crítico (FL-02 pasos 7–8 y FL-04 completo).

El destinatario (email del alumno) es **PII** y debe cifrarse en reposo (AES-256), igual que la PII de `Usuario` en C-07. El despacho debe ser asíncrono (worker de cola) para no bloquear la petición HTTP del docente, y los envíos masivos requieren una etapa de aprobación humana configurable por tenant (RN-17).

## What Changes

- **Nuevo modelo `Comunicacion`** (tabla `comunicacion`): `destinatario` cifrado (AES-256-GCM vía `EncryptedString`), `lote_id` para agrupar envíos masivos, `asunto`, `cuerpo`, `estado` (enum), `materia_id`, `enviado_por`, `enviado_at` nullable, `error_detalle` nullable. Sobre `TenantScopedBase` (soft delete, `tenant_id`).
- **Máquina de estados** (RN-15) con transiciones válidas explícitas:
  - `Pendiente → Enviando → Enviado`
  - `Pendiente → Enviando → Error`
  - `Pendiente → Cancelado`
  - `Enviando → Error` (fallo durante el despacho)
  - Toda otra transición es inválida y debe rechazarse con excepción de dominio.
- **Preview obligatorio** antes de encolar (F3.1, RN-16): endpoint que renderiza asunto+cuerpo con sustitución de variables de plantilla, sin escribir en DB ni encolar.
- **Encolado masivo** (F3.2): crea N filas `Comunicacion` en estado `Pendiente` bajo un mismo `lote_id`.
- **Configuración por tenant** (`tenant_config`): nueva tabla clave/valor de settings por tenant, que aloja el flag `aprobacion_comunicacion_requerida` y queda extensible a futuros flags.
- **Aprobación humana configurable por tenant** (F3.3, RN-17): guard `comunicacion:aprobar`, flag leído desde `tenant_config`. Aprobar/cancelar a nivel **lote** o **individual**. Si la aprobación está activa para el tenant, los mensajes masivos quedan en `Pendiente` hasta aprobación; el worker NO los toma sin aprobación.
- **Worker asíncrono de despacho** (`workers/`, ADR-003): **polling sobre la tabla `comunicacion`** (la tabla ES la cola; sin broker ni N8N), transiciona `Pendiente → Enviando → Enviado/Error`, respeta la aprobación, registra `enviado_at` y `error_detalle`. `Error` es estado terminal (sin reintento automático). Reemplaza el placeholder no-op de `backend/app/workers/main.py`. El envío físico se aísla tras una interfaz `EmailSender` (Protocol) con un `TestSender`.
- **Plantillas con variables de sustitución** (ej. `{nombre}`, `{materia}`): motor de render puro y testeable que **falla fuerte** ante una variable sin resolver (no encola ni envía con marcadores abiertos); validado en el preview.
- **Scope `propio` del PROFESOR**: al encolar, el PROFESOR solo comunica a destinatarios de sus comisiones, validado contra `Asignacion` (C-07).
- **Endpoints `/api/comunicaciones/*`** (guard `comunicacion:enviar`): preview, encolar, aprobar/cancelar lote, aprobar/cancelar individual, consultar estado del lote.
- **Auditoría**: nueva acción `COMUNICACION_ENVIAR` en el catálogo `audit_action` (ADD VALUE idempotente), registrada al encolar y al aprobar.
- **Migración `009`** (`down_revision="008"`): crea enum `comunicacion_estado`, tabla `comunicacion`, tabla `tenant_config`, e idempotentemente agrega `COMUNICACION_ENVIAR` al enum `audit_action`. Los permisos `comunicacion:enviar` y `comunicacion:aprobar` **ya existen** en el seed RBAC (migración 003) — no se re-crean.

## Non-Goals

- **Proveedor de email real** (SMTP / servicio transaccional / N8N): en C-12 el envío se aísla tras `EmailSender` con un `TestSender`; la integración real es un change futuro.
- **Cola basada en broker** (Redis / ARQ / Celery) u orquestación N8N: la cola de C-12 es la propia tabla `comunicacion` (polling); migrar a broker es un change futuro.
- **Reintentos automáticos / backoff**: `Error` es estado terminal en C-12; reintentar es una re-acción manual (re-encolar).
- **Mensajería interna entre usuarios / comunicación entre docentes** (F3.4 / FL-10): fuera de scope, es otro módulo.
- **Frontend** (panel de comunicaciones): corresponde a un change de frontend.

## Capabilities

### New Capabilities
- `comunicaciones`: modelo de comunicación saliente con PII cifrada, máquina de estados (RN-15), preview obligatorio (RN-16), encolado masivo por lote, aprobación humana configurable por tenant (RN-17), worker de despacho asíncrono y endpoints protegidos por RBAC con auditoría.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos. Los permisos comunicacion:* ya existen en rbac-permission-catalog (seed 003); audit-action-catalog se EXTIENDE con COMUNICACION_ENVIAR pero ese catálogo es abierto por diseño (ADD VALUE idempotente), no un cambio de requisito de comportamiento. -->

## Impact

- **Backend nuevo**: `models/comunicacion.py`, `models/tenant_config.py`, `repositories/comunicacion_repository.py`, `repositories/tenant_config_repository.py`, `services/comunicacion_service.py`, `services/comunicacion_estados.py` (máquina de estados pura), `services/comunicacion_plantilla.py` (render de variables, puro), `api/v1/routers/comunicaciones.py`, `schemas/comunicacion.py`.
- **Worker**: `backend/app/workers/` — `comunicacion_worker.py` (loop de polling sobre la tabla) + `email_sender.py` (Protocol `EmailSender` + `TestSender`); reemplaza el placeholder de `main.py`.
- **Migración**: `backend/alembic/versions/009_create_comunicaciones.py` (enum `comunicacion_estado` + tablas `comunicacion` y `tenant_config` + extend `audit_action`).
- **Auditoría**: extiende `app/models/audit.py` (enum `AuditAction`) con `COMUNICACION_ENVIAR`.
- **RBAC**: sin cambios de seed (permisos ya existen).
- **Multi-tenancy / seguridad**: `tenant_id` en `comunicacion`; identidad y tenant desde JWT; `destinatario` cifrado AES-256; soft delete.
- **Governance: ALTO** — este change toca worker de despacho, PII cifrada y un flujo de aprobación. El apply requiere checkpoint de aprobación humana (tarea 0.1). Las 7 preguntas abiertas que elevó este change ya fueron **resueltas por el usuario** y están documentadas como decisiones cerradas en `design.md` (sección "Decisiones resueltas"): cola por polling de la tabla, flag de aprobación en `tenant_config`, `EmailSender` + `TestSender`, plantilla que falla fuerte, `Error` terminal, scope `propio` del PROFESOR contra `Asignacion`, y mensajería interna fuera de scope.
