# Pendientes y deuda técnica

> Backlog verificado contra `master` el **2026-06-11**. El historial de fixes ya mergeados
> (enums, teardowns de `audit_event`, impersonación RN-41, scope de `listar_instancias`,
> selectores buscables, ADMIN scope global + umbral por-materia, y los fixes del flujo
> COORDINADOR del 2026-06-11 — dropdowns/`estructura:ver`, umbral COORDINADOR, DELETE de
> encuentros, selects de coloquios, crear cohorte en el wizard, notificación de tareas vía
> mensajería, nav Liquidaciones deshabilitado) vive en git y en Engram. Se removió de este
> doc por ruido.

> **No queda deuda técnica accionable dentro de scope.** Todo lo abierto está bloqueado por
> preguntas de negocio sin cerrar (ver abajo) y no se toca sin desbloquearlas.

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
  Los ítems `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria` siguen siendo placeholders
  a 404 deliberados. No gatear ni "arreglar" sin pedido explícito.
- **RN-28 (CSRF)**: probablemente N/A con auth JWT por header `Authorization` (no cookie).
  Requiere decisión arquitectónica, no es bug.
