# Tasks — C-29 frontend-admin-core

> Strict TDD: por cada componente/service/hook, test que falla → mínimo código → triangular → refactor.
> Componentes React <200 LOC, sin `any`, PascalCase. Todo fetch por hooks de `services/`.
> Identidad/tenant SIEMPRE por JWT, nunca en el body. Cero referencia a C-18/finanzas.

## 1. Estructura académica — feature `admin-estructura` (governance MEDIO)

- [x] 1.1 Crear `features/admin-estructura/types/index.ts` con tipos derivados de `CarreraRead/MateriaRead/CohorteRead` y de los `*Create`/`*Update` (incluye `EstadoEstructura`). Sin `any`.
- [x] 1.2 TDD: `services/estructuraAdminService.ts` — funciones `listar/crear/editar/darBaja` para carreras, materias y cohortes sobre `/api/v1/admin/{carreras,materias,cohortes}`, envueltas con `parseDomainError` (espejo de `asignacionService`). Test del service primero.
- [x] 1.3 TDD: `hooks/estructuraHooks.ts` — `useQuery` de catálogos + `useMutation` (crear/editar/baja) con invalidación de queries por entidad.
- [x] 1.4 TDD: componentes de tabla ABM por entidad (carreras/materias/cohortes) reutilizando el patrón `AsignacionesTable`; filtros client-side estilo `AsignacionesFilters`.
- [x] 1.5 TDD: formularios RHF + Zod de alta/edición por entidad; cohorte con `carrera_id` requerido y `vig_hasta` nullable (reusar lógica de `PasoCohorte`). Manejo de 409 (unicidad/inactiva/cohortes-abiertas) y 404 con mensaje de `parseDomainError`.
- [x] 1.6 TDD: `pages/AdminEstructuraPage.tsx` con secciones/tabs por entidad y gate `Forbidden403` para no-ADMIN (patrón `SetupCuatrimestrePage`).

## 2. Usuarios del tenant — feature `admin-usuarios` (governance CRÍTICO)

- [ ] 2.1 **CHECKPOINT GOVERNANCE (CRÍTICO)**: describir al usuario el set EXACTO de campos del form (solo no-PII de `UsuarioRead`/`UsuarioCreate`), el flujo alta/edición/baja y el gate `Forbidden403`; **esperar confirmación humana antes de escribir código** de esta feature.
- [ ] 2.2 Crear `features/admin-usuarios/types/index.ts` con tipos de `UsuarioRead/UsuarioCreate/UsuarioUpdate` SOLO con campos no-PII (NUNCA dni/cuil/cbu/alias_cbu).
- [ ] 2.3 TDD: `services/usuarioAdminService.ts` — `listar/crear/editar/darBaja` sobre `/api/v1/admin/usuarios`, con `parseDomainError`. Test del service primero (incluye caso 409 `ConflictoEmail`).
- [ ] 2.4 TDD: `hooks/usuarioAdminHooks.ts` — query de lista + mutaciones con invalidación.
- [ ] 2.5 TDD: tabla de usuarios (columnas no-PII) + form RHF/Zod de alta/edición con solo campos no-PII; confirmación previa a la baja (`DELETE` 204 = soft delete). Test que verifica que el form NO renderiza campos PII.
- [ ] 2.6 TDD: `pages/AdminUsuariosPage.tsx` con gate `Forbidden403` para no-ADMIN.

## 3. Panel de auditoría — feature `admin-auditoria` (governance BAJO, read-only)

- [x] 3.1 Crear `features/admin-auditoria/types/index.ts` con tipos de `AuditEventRead`, los `*Item`/`*Response` de métricas y `UltimaAccionItem`.
- [x] 3.2 TDD: `services/auditoriaService.ts` — `listarEventos(limit,offset, filtros)` + funciones para las 4 métricas y `ultimas-acciones`. Solo lecturas; `parseDomainError`.
- [x] 3.3 TDD: `hooks/auditoriaHooks.ts` — `useQuery` por endpoint (listado paginado + métricas), sin mutaciones.
- [x] 3.4 TDD: tabla de eventos con paginación por offset (deshabilitar "siguiente" si la página trae < `limit` filas) + filtros `desde`/`hasta`/`actor_user_id`.
- [x] 3.5 TDD: panel de métricas (acciones-por-día, interacciones-docente, interacciones-docente-materia, comunicaciones-por-docente) y últimas-acciones como tablas/KPIs.
- [x] 3.6 TDD: `pages/AdminAuditoriaPage.tsx` con gate `Forbidden403` para no-ADMIN.

## 4. Routing y navegación

- [x] 4.1 Registrar en `frontend/src/App.tsx` las rutas protegidas `/admin/estructura` y `/admin/auditoria` (admin-usuarios DIFERIDO — governance CRÍTICO, checkpoint pendiente).
- [x] 4.2 Actualizar `frontend/src/features/shell/components/buildNav.ts`: actualizar comentario de cabecera para reflejar que /admin/estructura y /admin/auditoria ya están registradas; /admin/usuarios sigue deferred.
- [x] 4.3 TDD: test de `buildNav` confirmando que los 3 ítems siguen visibles solo para ADMIN y que `Liquidaciones` sigue `disabled`.

## 5. Verificación final

- [x] 5.1 Correr la suite de tests del frontend; cobertura de las 3 features verde (≥80% líneas). Resultado: 116/116 tests pasados (10 suites).
- [x] 5.2 Verificar grep en las 3 features nuevas: cero referencias a liquidaciones/facturas/C-18 y cero PII financiera en forms/tablas de usuarios. Confirmado 0 matches.
- [x] 5.3 Confirmar que ningún componente llama a `apiClient` directo (todo pasa por hooks de `services/`) y que ningún body incluye tenant_id/identidad. Confirmado: apiClient solo en services/ y sus tests.
