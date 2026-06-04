## Context

Tras C-01..C-07 el sistema tiene: JWT con `get_current_user` (user_id, tenant_id, roles), tenancy row-level (`TenantScopedRepository`), RBAC fail-closed, auditoría append-only, catálogo estructural (Carrera/Cohorte/Materia) y entidades de identidad/autorización (Usuario/Asignacion). La última migración aplicada es **006**.

C-09 agrega el **padrón versionado** de alumnos por materia×cohorte y el **primer cliente de integración con Moodle WS**. Es la entidad que todos los módulos de calificaciones, análisis y comunicaciones necesitan como raíz: sin `EntradaPadron` no hay alumno al que trackear ni a quien enviar un mensaje.

Infraestructura reutilizada sin modificar:
- **`EncryptedString`** (C-02): cifra `EntradaPadron.email` (AES-256-GCM, nonce 12 bytes, app-layer).
- **`TenantScopedRepository`** (C-02): filtrado por `tenant_id` y `deleted_at IS NULL` por defecto.
- **`require_permission`** + `get_current_user` (C-03/C-04): guard fail-closed en cada endpoint.
- **`AuditLog`** + helper de auditoría (C-05): registro de `PADRON_CARGAR`.

Tensión a resolver: la KB §E6 modela el padrón como **versionado** (conserva historial de cargas) pero RN-05 describe la importación como un **"upsert destructivo"** (el anterior queda reemplazado). La reconciliación es: `activa=True` como cursor único por `(tenant_id, materia_id, cohorte_id)` — hay una sola versión activa en todo momento, pero las anteriores no se borran físicamente (soft-inactivación). El historial se conserva; desde la perspectiva del negocio, el sistema opera con el padrón activo, cumpliendo RN-05.

## Goals / Non-Goals

**Goals:**
- Modelos `VersionPadron` y `EntradaPadron` tenant-scoped con soft-delete; `EntradaPadron.email` cifrado con `EncryptedString`.
- Versionado activo único por `(tenant_id, materia_id, cohorte_id)`: activar nueva versión desactiva la anterior de forma atómica en la misma transacción.
- Importación desde archivo `.xlsx`/`.csv` con **vista previa** (parse sin guardar) y **confirmación** (guarda + activa) como dos llamadas distintas.
- Vaciado scope-isolated (RN-04): PROFESOR solo puede vaciar versiones que él mismo cargó; COORDINADOR puede vaciar cualquier versión de su tenant.
- Cliente Moodle WS (`integrations/moodle_ws.py`) con sync on-demand y nocturna; errores → `502` con reintento simple.
- Fallback manual: si Moodle WS no está disponible, la importación manual (xlsx/csv) siempre funciona.
- Permiso nuevo `padron:cargar`, migración **007** con tablas `version_padron` y `entrada_padron`.
- Auditoría `PADRON_CARGAR` en cada activación exitosa.

**Non-Goals:**
- NO se implementan calificaciones ni análisis de atrasados (C-10, C-11).
- NO se construye la integración de actividades de Moodle (solo usuarios/enroll en C-09; actividades van con calificaciones en C-10).
- NO se almacena el archivo de importación (se parsea en memoria y se descarta).
- NO se introduce almacenamiento de archivos (S3/objectstore) — fuera de scope del MVP.
- NO se modifica RBAC, auth ni auditoría existentes; C-09 solo los consume.
- NO se implementa el frontend (C-21+).

## Decisions

### D1 — Migración 007 (corrección del número indicado en CHANGES.md)
CHANGES.md dice "Migración 0NN": 005 y 006 ya están ocupadas (C-06 y C-07). La próxima libre es **007**. Archivo: `backend/alembic/versions/007_create_padron.py`, `revision="007"`, `down_revision="006"`. Se sigue el patrón de 005/006: SQL explícito, enums idempotentes, índices nombrados, seed idempotente de permisos.

### D2 — `activa` como cursor de versión activa, atómica con UPDATE
Para garantizar unicidad de la versión activa por `(tenant_id, materia_id, cohorte_id)` sin que el índice pueda quedar en estado inconsistente, la activación de una nueva versión ocurre así en la misma transacción de la sesión DB:
```sql
UPDATE version_padron SET activa = FALSE
 WHERE tenant_id = :tenant_id AND materia_id = :mid AND cohorte_id = :cid AND activa = TRUE;
INSERT INTO version_padron (..., activa = TRUE) VALUES (...);
```
No se usa un índice único parcial sobre `(tenant_id, materia_id, cohorte_id) WHERE activa = TRUE` porque la lógica de transición ya garantiza la unicidad y el índice parcial complicaría el rollback (el UPDATE precede el INSERT en la misma transacción).
**Alternativa descartada**: índice único parcial + `ON CONFLICT DO UPDATE` → genera un UPDATE implícito que no registra auditoría de forma limpia y complica la lectura del log.

### D3 — `EntradaPadron.email` cifrado con `EncryptedString`, sin blind index
El email de `EntradaPadron` es PII del alumno (regla dura #12). Se cifra con `EncryptedString` (AES-256-GCM, igual que `Usuario.email_encrypted`). A diferencia de `Usuario`, **no se agrega blind index** porque:
- No existe un caso de uso de búsqueda de `EntradaPadron` por email exacto en C-09.
- La búsqueda de alumnos se hace por nombre/apellidos/comision/regional (campos no cifrados).
- Si en el futuro se necesita "¿está este email en el padrón?", se agrega el blind index en ese change.
Esto sigue el principio de minimizar la superficie PII determinística (trade-off documentado en C-07 D2).

### D4 — `usuario_id` nullable: alumno sin cuenta es ciudadano de primera clase
`EntradaPadron.usuario_id` es nullable (FK → `usuario.id`, `ON DELETE SET NULL`). Un alumno puede existir en el padrón antes de tener cuenta en el sistema (KB §E6: "puede ser nulo si aún no tiene cuenta"). Los módulos de calificaciones (C-10) deben tolerar entradas sin `usuario_id`. La reconciliación alumno↔usuario (linkear por email en algún momento) es tarea futura.

### D5 — Import en dos pasos: preview (sin escritura) + confirm (escribe y activa)
El flujo de importación tiene dos endpoints distintos:
- `POST /api/v1/padron/preview` — recibe el archivo multipart, parsea (openpyxl para xlsx, csv stdlib para csv), devuelve JSON con filas detectadas, comisiones, regionales y errores de validación. **No escribe nada en DB.**
- `POST /api/v1/padron/activar` — recibe los datos ya parseados (como JSON, posiblemente la respuesta de preview más confirmación), escribe `VersionPadron` + `EntradaPadron` y desactiva la versión anterior. Exige el mismo permiso `padron:cargar`.
Este diseño evita re-parsear el archivo en el segundo paso. El cliente envía el payload JSON (que recibió de preview) como body del confirm. **No se guarda el archivo** en DB ni disco.
**Alternativa considerada**: un único endpoint con flag `dry_run=True/False`. Descartada: dos endpoints hace la intención explícita y evita errores accidentales de importación sin preview.

### D6 — Vaciado scope-isolated (RN-04)
`DELETE POST /api/v1/padron/vaciar?materia_id=X&cohorte_id=Y`:
- **PROFESOR** (`padron:cargar`): puede desactivar y marcar deleted_at en las entradas **solo de la versión activa que él mismo cargó** (`cargado_por = current_user.id`). Si la versión activa fue cargada por otro, recibe 403.
- **COORDINADOR/ADMIN** (`padron:gestionar`): puede vaciar cualquier versión activa de su tenant.
El soft-delete sobre `EntradaPadron` es el patrón estándar del repo (set `deleted_at = now()`). La `VersionPadron` queda con `activa = False` y su `deleted_at` también.

### D7 — MoodleWSClient: async httpx, token por tenant desde settings
`integrations/moodle_ws.py` implementa un cliente async (`httpx.AsyncClient`) con:
- Configuración: `MOODLE_BASE_URL` y `MOODLE_TOKEN` por tenant (leídos de `Settings` o desde una futura tabla de configuración de tenant; en C-09 se usa `.env` como primera aproximación).
- Método `get_enrolled_users(course_id: int) → list[dict]`: llama `core_enrol_get_enrolled_users` del WS de Moodle.
- Reintento simple: 2 intentos con sleep de 2s entre ellos usando asyncio; si ambos fallan → `raise MoodleWSError(502, ...)`.
- El servicio atrapa `MoodleWSError` y lo propaga como `HTTPException(502)`.
- Sync nocturna: `asyncio.create_task` lanzado en el `lifespan` de FastAPI, que corre a una hora configurable (`MOODLE_SYNC_HOUR`, defecto 3am UTC). En C-09 no se usa Celery ni ARQ; la tarea corre en el mismo proceso (suficiente para MVP).
**Alternativa descartada**: N8N como orquestador (ADR-003 aún no resuelto en C-09). Se pospone para cuando ADR-003 se cierre.

### D8 — Permiso `padron:cargar` y `padron:gestionar`
Dos permisos nuevos en la migración 007:
- `padron:cargar` (PROFESOR, COORDINADOR, ADMIN): importar y vaciar el propio scope.
- `padron:gestionar` (COORDINADOR, ADMIN): vaciar cualquier padrón del tenant.
Seed idempotente en 007 exactamente igual al patrón de 005/006.

### D9 — Patrón de archivos (igual a C-07)
- `backend/app/models/padron.py` — `VersionPadron` + `EntradaPadron`
- `backend/app/repositories/padron_repository.py` — `PadronRepository`
- `backend/app/services/padron_service.py` — `PadronService` (preview, activar, vaciar, sync_moodle)
- `backend/app/integrations/moodle_ws.py` — `MoodleWSClient`
- `backend/app/api/v1/routers/padron.py` — endpoints
- `backend/alembic/versions/007_create_padron.py`
Límite ≤500 LOC por archivo. Si `padron_service.py` supera el límite, se divide en `padron_import_service.py` y `moodle_sync_service.py`.

## Risks / Trade-offs

- **[Archivo en memoria]** → Si el xlsx tiene miles de filas (padrón muy grande), el parsing en memoria puede consumir RAM. Mitigación: límite de filas configurable (`PADRON_MAX_ROWS`, defecto 5000); si se supera, el servidor devuelve 422 con mensaje claro. Queda pendiente streaming para padrones masivos.
- **[Token Moodle único por instancia]** → En C-09 el token se lee de `.env`. Si el tenant tiene múltiples tokens (por instancia Moodle), esto no escala. Mitigación diferida: una tabla `tenant_moodle_config` en un change posterior. Documentado como deuda técnica.
- **[Sync nocturna en el mismo proceso]** → Sin Celery/ARQ, si el proceso se reinicia, la tarea se cancela. Para MVP con un solo nodo es aceptable. Si se adopta N8N (ADR-003), la sync nocturna migraría.
- **[Vaciado sin papelera]** → El soft-delete de entradas no tiene "deshacer". Si el docente vacía por error, debe reimportar. Trade-off aceptado: es comportamiento estándar de importación; la versión anterior (inactiva) sigue en DB para auditoría si se necesita recuperación manual.
- **[`activa` sin índice único parcial]** → La unicidad de la versión activa la garantiza la lógica del service (D2). Un bug en el service podría crear dos versiones activas. Mitigación: el `get_active_version` del repository siempre hace `ORDER BY cargado_at DESC LIMIT 1` como defensa extra.

## Open Questions

Ninguna bloqueante para apply. Notas diferidas:
- **OQ-1**: ¿Se guarda el archivo xlsx/csv como adjunto para auditoría? En C-09, NO (se parsea y descarta). Si se decide guardar, requiere objectstore (fuera de scope actual).
- **OQ-2**: ¿Cómo mapea `course_id` de Moodle a `(materia_id, cohorte_id)` de activia-trace? En C-09 se pide el mapeo manual vía parámetros del endpoint. Un mapeo automático requiere una tabla de configuración por tenant (change posterior).
- **OQ-3**: ADR-003 (worker de mails con N8N vs. asyncio) aplica también a la sync nocturna. Cuando ADR-003 se cierre, migrar la sync aquí si corresponde.
