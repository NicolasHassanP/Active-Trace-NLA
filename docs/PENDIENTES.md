# Pendientes y deuda técnica

> Backlog verificado contra `master` el **2026-06-11**. El historial de fixes ya mergeados
> (enums, teardowns de `audit_event`, impersonación RN-41, scope de `listar_instancias`,
> selectores buscables, ADMIN scope global + umbral por-materia, y los fixes del flujo
> COORDINADOR del 2026-06-11 — dropdowns/`estructura:ver`, umbral COORDINADOR, DELETE de
> encuentros, selects de coloquios, crear cohorte en el wizard, notificación de tareas vía
> mensajería, nav Liquidaciones deshabilitado) vive en git y en Engram. Se removió de este
> doc por ruido.

> **Único trabajo accionable abierto**: terminar C-29 (ver "En curso" abajo). El resto está
> bloqueado por preguntas de negocio sin cerrar (ver "Fuera de scope") y no se toca sin desbloquearlas.

---

## En curso — C-29 `frontend-admin-core` (apply parcial)

Carve-out de la parte NO-finanzas de C-24: frontend de admin sobre backends ya hechos (C-06/C-07/C-05/C-19), **cero dependencia/referencia a C-18**. Artefactos en `openspec/changes/c-29-frontend-admin-core/`.

- ✅ **`admin-estructura`** (`/admin/estructura`) y ✅ **`admin-auditoria`** (`/admin/auditoria`) — **IMPLEMENTADOS y mergeados (2026-06-11)**. 116/116 vitest + 44/44 buildNav, `tsc` limpio, cero PII / cero C-18. La pantalla de estructura ya permite crear carreras/materias/cohortes desde la UI (resuelve el viejo gap de "no había UI para crear materias").
- 🔲 **`admin-usuarios`** (`/admin/usuarios`) — **APROBADO por el usuario (2026-06-11), PENDIENTE de implementar** (governance CRÍTICO; se cortó por falta de tokens). El checkpoint humano (task 2.1) YA está aprobado — no hace falta volver a pedirlo. Alcance acordado:
  - Página gateada a ADMIN (`Forbidden403`), consume `admin_usuarios.py` (`usuarios:gestionar`).
  - Tabla read **no-PII** (nombre/apellidos/email/legajo/estado + resumen de asignaciones).
  - Form alta/edición SOLO con `email`, `nombre`, `apellidos`, `legajo`, `estado`. **EXCLUIR** PII financiera (dni/cuil/cbu/alias_cbu/banco/facturador); test que verifica que el form NO renderiza campos PII.
  - Baja = `DELETE` (soft delete) con confirmación.
  - Tasks **2.2–2.6** de `openspec/changes/c-29-frontend-admin-core/tasks.md` + ruta `/admin/usuarios` en `App.tsx` + desmarcar su ítem en `buildNav.ts`.
  - ⚠️ **Limitación conocida (backend C-07)**: `POST /usuarios` crea el perfil pero **no** credenciales de login (`auth_identity_id` opcional, sin backfill). Un usuario creado no puede loguearse hasta vincular auth — trabajo de backend aparte, fuera de C-29.
  - **Próximo paso**: `/opsx:apply c-29-frontend-admin-core` (solo task group 2).

---

## Fuera de scope (justificado — no tocar sin cerrar preguntas)

- **Aprovisionamiento programático de tenants**. El RBAC se siembra solo vía migraciones, que
  cubren los tenants existentes al momento de migrar; un tenant creado después no recibe
  roles/permisos y no hay servicio de onboarding. Bloqueante para multi-tenant productivo real.
  Governance **CRÍTICO** (multi-tenancy + RBAC), ligado a **C-24**. No se codea sin desbloquear
  sus preguntas y aprobación humana explícita.
- **C-18 (liquidaciones)** y **C-24 (frontend finanzas/admin)**: diferidos a fin de proyecto,
  bloqueados por **PA-22/PA-23** (claves de Plus, acumulación) y **PA-25** (semántica NEXO).
- **Estructura académica / catálogo de materias**: bloqueado por **PA-01**, **PA-07**.
- **Nav**: el ítem **Liquidaciones** se muestra deshabilitado ("Próximamente") hasta C-18/C-24.
  `/admin/estructura` y `/admin/auditoria` ya NO son placeholders (C-29, implementados);
  `/admin/usuarios` sigue cayendo en 404 hasta completar C-29 task 2 (ver "En curso").
- **RN-28 (CSRF)**: probablemente N/A con auth JWT por header `Authorization` (no cookie).
  Requiere decisión arquitectónica, no es bug.
