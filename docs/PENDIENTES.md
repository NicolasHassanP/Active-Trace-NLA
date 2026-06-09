# Pendientes y deuda técnica — handoff

> Backlog de trabajo abierto para atacar en una próxima sesión. Generado al cierre de la sesión del **2026-06-09** sobre la rama `style/design-handoff`.
> Detalle adicional en Engram (topic_keys citados en cada ítem). Ordenado por prioridad sugerida.

> ### 🔄 Actualización 2026-06-09 (sesión 2)
> Los ítems **1.1, 1.2, 2.1, 4.3** fueron **resueltos y verificados verdes**, pero **OneDrive revirtió los archivos** del working tree (el repo vive en OneDrive). El trabajo se re-aplica de forma mecánica siguiendo **[docs/HANDOFF-fixes-tests.md](HANDOFF-fixes-tests.md)** (plan detallado por-archivo). Lo único que sobrevivió y quedó **commiteado** (`fe840bc`) son los helpers de `conftest.py` + 3 tests de router migrados.
> Además se diagnosticó la suite roja completa (~233 fallos): casi todos eran **test-side** (C-28 `domain_user_id`, fixture `audit_action`, patrón AuthIdentity-FK) y están cubiertos en el handoff. Quedó **un bug real de producción** nuevo (ver §6.5).
> ⚠️ Sacar el repo de OneDrive (clonar en `C:\dev\…`) antes de re-editar, o el problema vuelve. Engram: `infra/onedrive-revierte-cambios`.

## Contexto rápido

Esta sesión resolvió: C1 (permisos programas/fechas rotos), Setup Cuatrimestre = ADMIN-only, fixtures C-28 de perfil/inbox, bug 422 del handler de validación, S2 (seed RBAC de `inbox:usar`/`perfil:editar` en producción vía migración 018), R1/R2/R3 (matriz §3.3 sincronizada + drift de seed corregido), gating de TUTOR fuera de `/padron`, y las páginas frontend **M2 (perfil)** y **M1 (guardias)**. Todo commiteado y pusheado en `style/design-handoff`.

Lo que queda abierto es lo de abajo.

---

## 1. Bugs reales (atacar primero)

### 1.1 `encuentros-coord` envía días en formato inválido — ✅ RESUELTO (revertido por OneDrive → re-aplicar via HANDOFF Tarea A)
> Se corrigió el enum a `'Lunes'…'Domingo'` (+ se detectó y arregló `InstanciaEncuentroEstado` con `'postergado'` inexistente, y los enums de `coloquios`). Verificado `tsc` 0 errores + vitest verde. Pasos exactos en HANDOFF §Tarea A.
- **Qué**: `frontend/src/features/encuentros-coord/` usa los valores de `DiaSemana` en minúscula ASCII (`'lunes'`, `'martes'`, `'miercoles'`…), pero el enum real del backend (`backend/app/models/encuentro.py`) es **capitalizado y con acentos**: `'Lunes'`, `'Martes'`, `'Miércoles'`, `'Jueves'`, `'Viernes'`, `'Sábado'`, `'Domingo'`.
- **Impacto**: la creación/filtrado de encuentros por día puede estar mandando valores que el backend rechaza (422) o que no matchean. Verificar end-to-end.
- **Dónde**: `frontend/src/features/encuentros-coord/` (types y componentes de selección de día). Referencia del valor correcto: `frontend/src/features/guardias/types/index.ts` (M1 lo dejó bien).
- **Prioridad**: ALTA (posible bug funcional en producción).
- **Engram**: `frontend/m1-guardias-page`.

### 1.2 Dos errores de TypeScript pre-existentes — ✅ RESUELTO (revertido por OneDrive → re-aplicar via HANDOFF Tarea A)
> `EvaluacionTipo`/`ReservaEstado` de coloquios estaban en minúscula (no matcheaban backend) y `onDelegar` quedaba sin usar en tareas (→ botón "Delegar"). `tsc --noEmit` queda en 0 errores.
- **Qué**: `npx tsc --noEmit` falla con 2 errores ajenos a lo trabajado esta sesión.
- **Dónde**: `frontend/src/features/coloquios/pages/ColoquiosPage.tsx` y `frontend/src/features/tareas/components/TareasAdminTable.tsx`.
- **Impacto**: el typecheck del proyecto no pasa limpio; puede romper CI si hay gate de tsc.
- **Prioridad**: MEDIA.

---

## 2. Deuda de infraestructura de tests

### 2.1 Teardown de fixtures incompatible con la inmutabilidad de `audit_event` — 🟡 PARCIAL (helper commiteado; migración por-test pendiente)
> ✅ Commiteado en `conftest.py`: helper `delete_audit_events_for_tenant(session, tenant_id)` que respeta el trigger de inmutabilidad (DISABLE/ENABLE TRIGGER). 🔲 Falta migrar los teardowns de `test_calificaciones`/`_router`, `test_padron`, `test_comunicacion_service`, `test_c27` para que lo usen (se revirtieron) → HANDOFF Tarea B. Engram: `tests/audit-event-teardown-strategy`.
- **Qué**: ~8 fixtures de test hacen `DELETE FROM audit_event WHERE tenant_id = :tid` en su limpieza. La tabla `audit_event` es append-only (trigger `audit_event_immutable()` instalado por `test_audit_migration.py`). Cuando ese test corre antes en la misma sesión, los `DELETE` fallan → errores de teardown en corridas de suite completa. En aislamiento pasan (el trigger no está instalado).
- **Síntoma**: `RestrictViolationError: audit_event rows are immutable` y/o `DependentObjectsStillExistError` al dropear `tenants`.
- **Dónde**: `backend/tests/` — `test_perfil_router.py`, `test_perfil_service.py`, `test_calificaciones*.py`, `test_padron.py`, `test_comunicacion_service.py`, `test_c27_historial_comunicaciones.py`, etc. (grep `DELETE FROM audit_event`).
- **Enfoque sugerido**: decidir una estrategia única — p.ej. no borrar audit_event en teardown de módulo y confiar en el `drop_all` de fin de sesión (conftest), o un helper de limpieza que respete la inmutabilidad. Es una decisión transversal de infra de tests.
- **Prioridad**: MEDIA (ruidoso, no rompe aserciones).

---

## 3. Feature pendiente

### 3.1 M3 — Gestión global de asignaciones (F4.3)
- **Qué**: página frontend dedicada para el ABM/gestión global de asignaciones docentes.
- **Estado**: backend `backend/app/api/v1/routers/asignaciones.py` 100% listo (GET/POST/PATCH/DELETE bajo `equipos:asignar`). Hoy solo se opera embebido en Setup Cuatrimestre; no hay página dedicada.
- **Enfoque**: misma receta que M1/M2 — feature `frontend/src/features/asignaciones/` con TDD (Vitest), reusando patrones de `features/equipos`/`features/guardias`. Ruta + nav para COORDINADOR/ADMIN (`equipos:asignar`).
- **Prioridad**: BAJA (valor bajo — ya existe vía operativa en Setup).

---

## 4. Deuda de arquitectura / seed

### 4.1 No hay aprovisionamiento programático de tenants
- **Qué**: el RBAC es per-tenant y se siembra solo vía migraciones, que cubren los tenants existentes **al momento de migrar**. Un tenant creado después no recibe roles/permisos automáticamente. No existe servicio de onboarding en `backend/app/`.
- **Impacto**: bloqueante para multi-tenant real; ligado a C-24 (ABM de usuarios/tenants no construido).
- **Prioridad**: MEDIA-ALTA cuando se encare multi-tenant productivo.
- **Engram**: `rbac/c20-permisos-seed-produccion`.

### 4.2 Gotcha: bases de dev pre-S2 necesitan re-aplicar grants
- **Qué**: cualquier base local sembrada antes de S2 no tiene `perfil:editar` para ALUMNO/NEXO/FINANZAS ni `inbox:usar` para NEXO/FINANZAS → 403 al editar perfil como ALUMNO. La base de dev de esta sesión ya fue corregida; **las de los compañeros no**.
- **Fix**: re-correr `backend/seed_rbac_demo.py` (idempotente) o aplicar migración 018, o SQL directo (`INSERT ... SELECT ... ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING`). Verificar: `perfil:editar` debe tener 7 roles, `inbox:usar` 6 (sin ALUMNO).
- **Prioridad**: BAJA (operativo por entorno).
- **Engram**: `infra/dev-db-grants-perfil-inbox`.

### 4.3 Permiso `guardias:registrar` sin uso — ✅ RESUELTO como reservado (revertido por OneDrive → re-aplicar via HANDOFF Tarea C)
> Decisión: documentarlo como RESERVADO en `seed_rbac_demo.py` (sin migración, sin tocar grants). Eliminarlo de raíz exigiría migración sobre RBAC (CRÍTICO) → no se hizo.
- **Qué**: existe en el catálogo RBAC (migración 003 + seed) pero ningún router lo usa — guardias se gatea con `encuentros:gestionar` (decisión C-13). Es un permiso muerto.
- **Enfoque**: o se elimina del catálogo, o se documenta como reservado. No urgente.
- **Prioridad**: BAJA.

---

## 5. Decisión de producto — NO tocar

### 5.1 Ítems de nav que llevan a 404 (intencional)
- **Qué**: `buildNav.ts` expone `/liquidaciones`, `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria`, que no tienen ruta en `App.tsx` → caen en 404.
- **Decisión tomada**: es deliberado. Quedan como vista placeholder hasta tener las herramientas para implementar esos changes (C-18 liquidaciones, C-24 admin/finanzas). **No gatear ni "arreglar" sin pedido explícito.**
- **Prioridad**: N/A (decisión cerrada).

---

## 6. Gaps de reglas de negocio (del análisis inicial)

Detectados en el análisis comparativo doc-vs-código; revisar si están en scope o diferidos:

- **RN-41 — Impersonación**: solo existe el andamiaje de auditoría (`audit_service.record_impersonation_start/end`, campo `impersonated_user_id`). No hay endpoint, middleware ni swap de sesión que la ejecute; el permiso `impersonacion:usar` no se consume. Dominio CRÍTICO. Confirmar si está diferido a un change futuro.
- **RN-28 — CSRF**: no implementado. Probablemente N/A si la auth es JWT por header `Authorization` (no cookie). Requiere decisión arquitectónica, no es bug claro.
- **RN-16 — Vista previa obligatoria de comunicaciones**: `preview_static()` existe pero el flujo no fuerza el preview antes de encolar (confianza media, verificar).
- **RN-11 — Jerarquía responsable docente**: el modelo `Asignacion.responsable_id` existe y persiste, pero sin lógica de validación de cadena/no-circular.

> Nota: RN-17 (aprobación masiva de comunicaciones) fue reportada como faltante en el análisis inicial pero **está implementada** (`comunicaciones.py` con `/aprobar-lote`, `/aprobar-individual`, etc. bajo `comunicacion:aprobar`). No es un gap.

### 6.5 🐛 `EncuentroService.listar_instancias` no filtra por asignaciones del PROFESOR — BUG REAL (nuevo)
- **Qué**: un PROFESOR ve instancias de encuentro que no son suyas; `listar_instancias` no aplica el scope propio por sus asignaciones. Lo destapa el test `test_encuentros::test_listar_encuentros_profesor_ve_solo_propios` (rojo legítimo), que antes estaba tapado por un error de FK en el setup.
- **Dónde**: `backend/app/services/encuentro_service.py`.
- **Governance**: MEDIO (dominio). Verificar la RN de scope antes de tocar.
- **Prioridad**: MEDIA-ALTA (fuga de visibilidad entre docentes).
- **Engram**: `tests/usuario-con-identidad-helper`.

### 6.6 Patrón de tests: usuario de dominio resoluble por JWT (helper ya disponible)
- **Qué**: para cualquier test de endpoint que necesite que el JWT `sub` resuelva a un `Usuario`, usar `create_usuario_con_identidad()` (ya en `conftest.py`, commiteado). NO setear `auth_identity_id` a mano (viola la FK a `auth_identities`). Invariante C-28: `auth_identity_id ≠ usuario.id`.
- **Engram**: `tests/usuario-con-identidad-helper`, `tests/c28-residual-buckets`.

---

## Fuera de scope (justificado, no tocar sin cerrar preguntas)

- **C-18 (liquidaciones)** y **C-24 (frontend finanzas/admin)**: pendientes con justificación; bloqueados por preguntas abiertas (PA-22/PA-23 Plus, etc.).
- Estructura académica / catálogo de materias: bloqueado por **PA-01**, **PA-07**.
- Rol **NEXO**: semántica completa diferida a **PA-25** (su set base ya está: `avisos:confirmar`, `equipos:ver`, `inbox:usar`, `perfil:editar`).
