# Pendientes y deuda técnica

> Backlog real verificado contra `master` el **2026-06-10**. Todo lo previo (fixes de enums, teardowns de `audit_event`, impersonación RN-41, scope de `listar_instancias`, etc.) ya está mergeado en master y se removió de este doc por ruido. El historial completo vive en Engram.

> ### ✅ Actualización 2026-06-10 (sesión 4) — ADMIN scope global + umbral por-materia implementado
> Diseño planificado por Nicolás (commit `505483b` en master) implementado con Strict TDD:
> - **Backend**: `UmbralMateria.asignacion_id` nullable + nueva col `cohorte_id`, migración `019_umbral_materia_scope_global.py` (partial indexes `uq_um_default_materia_cohorte` + `uq_um_asignacion_override`), `UmbralService.get_efectivo` con precedencia 3 niveles, router GET/PUT `/umbral` scope-aware (global → default materia/cohorte sin asignación; propio → override docente). 14 tests nuevos, 7/7 router previos.
> - **Frontend**: `buildNav.ts` saca ADMIN de "Mis materias"; tab Umbral dual → `UmbralConfigDefault` (ADMIN, info azul) + `UmbralConfigDocente` (docente, banner amarillo si hereda). 8 tests nuevos, tsc 0 errores.
>
> ### ✅ Actualización 2026-06-09 (sesión 3) — pendientes cerrados
> Tras `git pull` (compañero: impersonación RN-41 backend+frontend, enums coloquios, design assets) se cerraron y commitearon:
> - **Tarea B completa** (`66fa1a8` + `549e723`): teardowns `audit_event` migrados al helper de inmutabilidad en los 5 tests + 4 endpoint tests reescritos con `create_usuario_con_identidad` (patrón AuthIdentity-FK). Causa raíz del 500: el helper hacía `flush` sin `commit`, la sesión del endpoint no veía `auth_identities`. test_padron 25/25, test_calificaciones_router 7/7.
> - **Tarea A / §1.1 / §1.2** (`eeea808`): enums de `encuentros-coord` alineados al backend (`DiaSemana` capitalizado+acentos, `InstanciaEncuentroEstado` sin `'postergado'`). tsc 0 errores, 34 vitest verdes. (coloquios + TareasAdminTable ya los había hecho el compañero.)
> - **§6.5 bug producción** (`12cae5f`): `EncuentroService.listar_instancias` ahora aísla por asignación propia del docente (RN-04), no por materia. Subquery `slot_id ∈ slots del actor` con scope tenant+soft-delete. test_encuentros 15/15.
> - Infra: OneDrive pausado (proceso killeado), Engram actualizado 1.14.5→1.16.1 (el `sync --import` ya funciona). **Pendiente restante**: Tarea C del HANDOFF (seed 4.3, comentario RESERVADO en `seed_rbac_demo.py`, BAJO).
>
> ### 🔄 Actualización 2026-06-09 (sesión 2)
> Los ítems **1.1, 1.2, 2.1, 4.3** fueron **resueltos y verificados verdes**, pero **OneDrive revirtió los archivos** del working tree (el repo vive en OneDrive). El trabajo se re-aplica de forma mecánica siguiendo **[docs/HANDOFF-fixes-tests.md](HANDOFF-fixes-tests.md)** (plan detallado por-archivo). Lo único que sobrevivió y quedó **commiteado** (`fe840bc`) son los helpers de `conftest.py` + 3 tests de router migrados.
> Además se diagnosticó la suite roja completa (~233 fallos): casi todos eran **test-side** (C-28 `domain_user_id`, fixture `audit_action`, patrón AuthIdentity-FK) y están cubiertos en el handoff. Quedó **un bug real de producción** nuevo (ver §6.5).
> ⚠️ Sacar el repo de OneDrive (clonar en `C:\dev\…`) antes de re-editar, o el problema vuelve. Engram: `infra/onedrive-revierte-cambios`.

## Contexto rápido

Esta sesión resolvió: C1 (permisos programas/fechas rotos), Setup Cuatrimestre = ADMIN-only, fixtures C-28 de perfil/inbox, bug 422 del handler de validación, S2 (seed RBAC de `inbox:usar`/`perfil:editar` en producción vía migración 018), R1/R2/R3 (matriz §3.3 sincronizada + drift de seed corregido), gating de TUTOR fuera de `/padron`, y las páginas frontend **M2 (perfil)** y **M1 (guardias)**. Todo commiteado y pusheado en `style/design-handoff`.

Lo que queda abierto es lo de abajo.

> ### ✅ Cerrados 2026-06-10 (commits f3bd49b · ec147b4 · 5a8b94e · 670d988)
> - **M3 — página frontend de asignaciones (F4.3)**: feature `frontend/src/features/asignaciones/` completa + ruta/nav gateadas a COORDINADOR/ADMIN (`equipos:asignar`). 34 tests Vitest.
> - **RN-11 — jerarquía acíclica de responsable docente**: validación BFS en `usuario_service` (vía `usuario_repository`) que prohíbe auto-referencia y ciclos transitivos en `crear/editar_asignacion`. 7 tests pytest.
> - **RN-16 — vista previa obligatoria de comunicaciones**: gate `previewConfirmed` en `ComposeComunicacion.tsx` (Encolar deshabilitado hasta previsualizar). Enforcement en frontend por diseño (un flag backend sería inverificable; RN-17 cubre la autorización).
> - **Fix colateral**: `ComunicacionesPage` volvía a abrir en tab "Historial" por default sin destinatarios, contra C-27/D5 → restaurado "Componer".

---

## Vivo (deuda real)

| # | Ítem | Dónde | Prioridad |
|---|------|-------|-----------|
| 1 | **Aprovisionamiento programático de tenants**. El RBAC se siembra solo vía migraciones, que cubren los tenants existentes al migrar. Un tenant creado después no recibe roles/permisos. No hay servicio de onboarding. Bloqueante para multi-tenant real. | `backend/app/` (sin servicio de provisioning) | MEDIA-ALTA cuando se encare multi-tenant productivo; ligado a C-24 |

> **Nota**: este único ítem vivo es de governance **CRÍTICO** (multi-tenancy + RBAC) y está atado a **C-24** (diferido por PA-22/23/25). No se codea sin desbloquear esas preguntas y aprobación humana explícita.

---

## ✅ Cerrado 2026-06-11 — ADMIN scope global + umbral por-materia (implementado)

> Governance **CRÍTICO**. El diseño planificado el 2026-06-10 se implementó con Strict TDD (commit `409fadf`, integrado a master vía merge `a005478`). Detalle completo en git/Engram; resumen:
> - **Backend**: `UmbralMateria.asignacion_id` nullable + nueva col `cohorte_id`; migración `019_umbral_materia_scope_global.py` con partial indexes `uq_um_default_materia_cohorte` + `uq_um_asignacion_override`; `UmbralService.get_efectivo` con precedencia 3 niveles (override docente → default materia/cohorte → 60%); router GET/PUT `/umbral` scope-aware (global → default sin asignación; propio → override). Migración de datos: filas previas se vuelven overrides. 14 tests nuevos + 7/7 router previos.
> - **Frontend**: `buildNav.ts` saca ADMIN de "Mis materias"; tab Umbral dual → `UmbralConfigDefault` (ADMIN) + `UmbralConfigDocente` (docente, banner si hereda). 8 tests, tsc 0 errores.

---

## ✅ Cerrado 2026-06-11 — selectores buscables (follow-up UX, BAJA)

> Reemplazo de inputs de UUID crudo por selectores. Implementado con Strict TDD (rama `feat/selectores-buscables-followup`). Lo hecho:
> - **Backend**: nuevo `GET /api/v1/inbox/usuarios?q=` gateado `inbox:usar` (reusa `buscar_asignables`, no-PII). 6 tests pytest. Gotcha: la ruta literal `/usuarios` va declarada antes de `/{hilo_id}` o FastAPI la parsea como UUID.
> - **Componentes**: `UsuarioCombobox` ahora acepta prop opcional `searchHook` (inyectable); nuevo `UsuarioMultiCombobox` (multi-select con chips).
> - **`AsignacionMasivaForm`**: usuarios → multi-combobox; materia/cohorte → `<select>` por nombre.
> - **`AsignacionForm`**: materia/cohorte → `<select>` por nombre.
> - **`NuevoHiloForm`**: destinatario → `UsuarioCombobox` con `useBuscarUsuariosInbox` (pega al endpoint nuevo).
> - **`TareasFilters`**: docente → `UsuarioCombobox` (default hook; la página está gateada a COORDINADOR/ADMIN, que tienen `equipos:asignar` → sin riesgo 403); materia → `<select>`.
> - 145 tests frontend+backend verdes, tsc 0 errores.

### 🟡 Pendiente residual (BAJA) — select de carrera
El campo **`carrera_id`** en `AsignacionForm` y `AsignacionMasivaForm` quedó como `<input>` UUID con `// TODO`, porque **no existe endpoint `/admin/carreras`** (ni servicio frontend de carreras). Para cerrarlo: exponer ese endpoint backend (listar carreras por tenant) y reemplazar los dos inputs por `<select>` por nombre.

---

## QA manual pendiente (rol COORDINADOR)

> Checklist de verificación manual todavía sin cubrir, heredado de la sesión de testeo del 2026-06-07. Las secciones ya testeadas y los bugs encontrados (toast `undefined filas`, búsqueda por `apellidos`, filtros Comisión/Regional, columnas en Seguimiento) ya están fixeados en master. Credenciales demo en `DEMO_BOOTSTRAP.md`.

- **Padrón** (`/padron`): importar CSV real y verificar el conteo del toast; vaciar padrón y confirmar que Seguimiento queda vacío.
- **Atrasados** (`/atrasados`): con calificaciones cargadas, confirmar que aparecen atrasados; seleccionar alumnos y usar "Comunicar a seleccionados"; filtros por comisión y regional.
- **Monitor** (`/monitor`): verificar nombre/apellido (misma fix de Seguimiento); filtros de materia, cohorte, estado.
- **Mensajería** (`/mensajes`): iniciar y responder un hilo; nombre del participante (no UUID); deep link `?hilo=<id>`; badge de campanita suma avisos + mensajes no leídos; animación al recibir mensaje.
- **Equipos docentes** (`/equipos`): asignar tutor/profesor a una comisión y verificar persistencia tras recargar.
- **Encuentros** (`/encuentros`): crear, editar y eliminar un encuentro.
- **Coloquios** (`/coloquios`): crear un coloquio y gestionar inscripciones.
- **Tareas** (`/tareas`): crear una tarea de seguimiento y marcarla completada.
- **Setup cuatrimestre** (`/setup-cuatrimestre`): completar el flujo de setup inicial.
- **Seguridad transversal**: logout + acceso directo a `/padron` → redirige al login; COORDINADOR no accede a rutas `/admin/*`.

---

## Fuera de scope (justificado — no tocar sin cerrar preguntas)

- **C-18 (liquidaciones)** y **C-24 (frontend finanzas/admin)**: diferidos a fin de proyecto, bloqueados por **PA-22/PA-23** (claves de Plus, acumulación) y **PA-25** (semántica NEXO).
- **Estructura académica / catálogo de materias**: bloqueado por **PA-01**, **PA-07**.
- **Nav a 404 intencional**: `/liquidaciones`, `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria` son placeholders deliberados hasta C-18/C-24. No gatear ni "arreglar" sin pedido explícito.
- **RN-28 (CSRF)**: probablemente N/A con auth JWT por header `Authorization` (no cookie). Requiere decisión arquitectónica, no es bug.
