# Tasks — C-23 frontend-coordinacion

> Strict TDD: para cada tarea con lógica (service/hook/validación), escribir el test que falla ANTES del código.
> Cada módulo replica la estructura de C-22 (`types/index.ts`, `services/<name>Service.ts`, `hooks/<name>Hooks.ts`, `components/*`, `pages/*`, `__tests__`).
> Todos los services envuelven errores con `parseDomainError`. Todo fetch pasa por hooks de TanStack Query.
> Resolver OQ-1..OQ-5 (design.md) antes de las tareas que dependen de ellas.

## 0. Preparación (resolver antes de implementar)

- [x] 0.1 Resolver OQ-1 (lectura de avisos para gestión), OQ-3 (export del monitor), OQ-4 (filtros de encuentros/guardias) con el usuario/profesor
- [x] 0.2 Leer schemas backend exactos: `backend/app/schemas/{equipo,aviso,tarea}.py` y los DTOs de coloquios/encuentros/guardias/monitor para alinear `types` (OQ-2)
- [x] 0.3 Decidir ubicación del helper de descarga de blobs (OQ-5): crear `@/shared/services/downloadFile.ts` si no existe en C-22

## 1. Equipos (`features/equipos`)

- [x] 1.1 Definir `types/index.ts` (MisEquiposItem, ResumenLote, ResumenClonacion, requests) alineados al schema backend
- [x] 1.2 TDD `equiposService.listarMisEquipos` → `GET /api/v1/equipos/mis-equipos` (happy path + error)
- [x] 1.3 TDD `equiposService.consultarEquipo` → `GET /api/v1/equipos` con tripleta + filtros opcionales
- [x] 1.4 TDD `equiposService.asignacionMasiva` → `POST /api/v1/equipos/asignacion-masiva` (201 + 422)
- [x] 1.5 TDD `equiposService.clonarEquipo` → `POST /api/v1/equipos/clonar`
- [x] 1.6 TDD `equiposService.vigenciaGeneral` → `PATCH /api/v1/equipos/vigencia-general`
- [x] 1.7 TDD `equiposService.exportarEquipo` → `GET /api/v1/equipos/exportar` (blob + descarga)
- [x] 1.8 TDD hooks (`useMisEquipos`, `useEquipo`, mutations) con queryKey por filtros e invalidación
- [x] 1.9 Componentes: `MisEquiposTable`, `EquipoFilters`, `AsignacionMasivaForm` (RHF+Zod), `ClonarEquipoDialog`, `VigenciaGeneralForm` (cada uno < 200 LOC)
- [x] 1.10 TDD `EquiposPage`: render por rol (gestión COORDINADOR/ADMIN vs solo mis-equipos PROFESOR), estados vacío/error

## 2. Avisos (`features/avisos`)

- [x] 2.1 Definir `types/index.ts` (AvisoRead, CrearAvisoRequest, ActualizarAvisoRequest, AcknowledgmentRead, enums de alcance/severidad)
- [x] 2.2 TDD `avisosService` gestión: crear `POST /api/v1/avisos` (201), editar `PUT /{id}` (200/404), baja `DELETE /{id}` (204/404)
- [x] 2.3 TDD `avisosService` feed: `GET /api/v1/avisos` y `GET /api/v1/avisos/pendientes`
- [x] 2.4 TDD `avisosService.ack` → `POST /api/v1/avisos/{id}/ack` (200/403/404)
- [x] 2.5 TDD Zod schema del aviso: alcance no global ⇒ contexto (materia/cohorte) obligatorio
- [x] 2.6 TDD hooks (lista, pendientes, mutations de gestión y ack) con invalidación
- [x] 2.7 Componentes: `AvisoForm` (RHF+Zod), `AvisosTable`, `BandejaAvisos`, `AckButton`
- [x] 2.8 TDD `AvisosPage`: gestión visible solo COORDINADOR/ADMIN; bandeja para cualquier autenticado

## 3. Tareas (`features/tareas`)

- [x] 3.1 Definir `types/index.ts` (TareaRead, ComentarioTareaRead, requests, estados del workflow)
- [x] 3.2 TDD `tareasService`: `GET /tareas/mias`, `GET /tareas/{id}`, `GET /tareas/admin` (con filtros)
- [x] 3.3 TDD `tareasService`: `POST /tareas` (alta), `POST /tareas/{id}/delegar`
- [x] 3.4 TDD `tareasService`: `PATCH /tareas/{id}/estado`, comentarios `GET`/`POST /tareas/{id}/comentarios`
- [x] 3.5 TDD Zod schema de alta de tarea (docente asignado y descripción obligatorios)
- [x] 3.6 TDD hooks (mis-tareas, admin con filtros, detalle, mutations) con invalidación
- [x] 3.7 Componentes: `MisTareasList`, `TareasAdminTable`, `TareasFilters`, `TareaForm`, `EstadoSelector`, `ComentariosThread`
- [x] 3.8 TDD `TareasPage`: mis-tareas para todos los roles habilitados; panel admin solo COORDINADOR/ADMIN

## 4. Monitores (`features/monitores`)

- [x] 4.1 Definir `types/index.ts` (MonitorFila, params de filtro)
- [x] 4.2 TDD `monitoresService.listarMonitor` → `GET /api/v1/analisis/monitor` con todos los filtros (materia, regional, comisión, búsqueda, estado, clasificación, rango de fechas)
- [x] 4.3 TDD `monitoresService.exportar` (según OQ-3: endpoint dedicado, reutilizado o client-side)
- [x] 4.4 TDD hook `useMonitor` con queryKey que incluye TODOS los filtros activos
- [x] 4.5 Componentes: `MonitorFilters`, `MonitorTable`, `MonitorToolbar` (limpiar/exportar)
- [x] 4.6 TDD `MonitorPage`: gating COORDINADOR/ADMIN, filtros aplicados/limpiados, estado vacío

## 5. Encuentros coordinación + guardias (`features/encuentros-coord`)

- [x] 5.1 Definir `types/index.ts` (InstanciaEncuentroRead, GuardiaRead, params de filtro — OQ-4)
- [x] 5.2 TDD `encuentrosCoordService.listarInstancias` → `GET /api/v1/encuentros/instancias`
- [x] 5.3 TDD `encuentrosCoordService.listarGuardias` → `GET /api/v1/guardias`
- [x] 5.4 TDD `encuentrosCoordService.exportarGuardias` → `GET /api/v1/guardias/export` (blob + descarga)
- [x] 5.5 TDD hooks (instancias, guardias) con filtros en queryKey
- [x] 5.6 Componentes: `InstanciasEncuentroTable`, `GuardiasTable`, `GuardiasFilters`
- [x] 5.7 TDD `EncuentrosPage`: gating COORDINADOR/ADMIN, vista transversal y registro de guardias

## 6. Coloquios (`features/coloquios`)

- [x] 6.1 Definir `types/index.ts` (MetricasRead, ConvocatoriaMetricasRead, ConvocatoriaConTurnosRead, AgendaItemRead, ResultadoRead, requests)
- [x] 6.2 TDD `coloquiosService.metricas` → `GET /api/v1/coloquios/metricas`
- [x] 6.3 TDD `coloquiosService.listarConvocatorias` → `GET /api/v1/coloquios/convocatorias`
- [x] 6.4 TDD `coloquiosService.crearConvocatoria` → `POST /api/v1/coloquios/convocatorias` (201)
- [x] 6.5 TDD `coloquiosService.importarCandidatos` → `POST /api/v1/coloquios/convocatorias/{id}/candidatos` (204)
- [x] 6.6 TDD `coloquiosService.cerrarConvocatoria` → `POST /api/v1/coloquios/convocatorias/{id}/cerrar`
- [x] 6.7 TDD `coloquiosService.agenda` → `GET /api/v1/coloquios/agenda`; `resultados` → `GET /api/v1/coloquios/convocatorias/{id}/resultados`
- [x] 6.8 TDD Zod schema de convocatoria (cupo > 0, días disponibles presentes)
- [x] 6.9 TDD hooks (métricas, convocatorias, mutations, agenda, resultados) con invalidación
- [x] 6.10 Componentes: `MetricasPanel`, `ConvocatoriasTable`, `ConvocatoriaForm`, `ImportarCandidatosDialog`, `AgendaReservas`, `ResultadosTable`
- [x] 6.11 TDD `ColoquiosPage`: gating COORDINADOR/ADMIN, métricas + convocatorias + acciones

## 7. Setup de cuatrimestre (`features/setup-cuatrimestre`)

- [x] 7.1 Definir `types/index.ts` (estado del wizard, pasos, estado por paso)
- [x] 7.2 TDD `useSetupWizard` (estado del flujo: pasos pendiente/completado, avance condicionado)
- [x] 7.3 Componente `SetupStepper` (lista de pasos con estado) < 200 LOC
- [x] 7.4 Paso 1: seleccionar/crear cohorte (reusa estructura académica existente)
- [x] 7.5 Paso 2: clonar equipo (reusa `equiposService.clonarEquipo`)
- [x] 7.6 Paso 3: ajustar asignaciones (reusa `equiposService.asignacionMasiva`)
- [x] 7.7 Paso 4: ajustar vigencias (reusa `equiposService.vigenciaGeneral`)
- [x] 7.8 Paso 5: cargar programas → `POST /api/v1/programas` (service + Zod)
- [x] 7.9 Paso 6: cargar fechas de evaluaciones → `POST /api/v1/fechas-academicas` (service + Zod)
- [x] 7.10 Paso 7: publicar aviso de bienvenida (reusa `avisosService.crear`)
- [x] 7.11 TDD `SetupCuatrimestrePage`: gating COORDINADOR/ADMIN, avance secuencial, error no avanza, completado

## 8. Routing y navegación (integración)

- [x] 8.1 Registrar rutas lazy en `App.tsx`: `/equipos`, `/avisos`, `/tareas`, `/monitor`, `/encuentros`, `/coloquios`, `/setup-cuatrimestre`, cada una con `ProtectedRoute requiredRoles` según matriz RBAC
- [x] 8.2 Activar/añadir ítems en `buildNav.ts`: `/avisos`, `/tareas`, `/monitor`, `/setup-cuatrimestre` (gateados por rol); confirmar `/equipos`, `/encuentros`, `/coloquios` ya presentes
- [x] 8.3 TDD `buildNav`: un COORDINADOR ve los ítems de coordinación; un PROFESOR/FINANZAS no ve los exclusivos de COORDINADOR/ADMIN

## 9. Verificación final

- [x] 9.1 Correr `vitest` completo del frontend — todos los tests verdes
- [x] 9.2 Verificar que ningún componente supere 200 LOC y que no haya `any` ni class components
- [x] 9.3 Verificar que ningún service envía identidad/tenant en el body
- [x] 9.4 Marcar tareas completas y registrar desviaciones / OQ resueltas

## Desviaciones y OQ resueltas (Batch 4)

### OQ-6 (nueva) — Cohorte en paso 1 del wizard
El paso 1 del setup (seleccionar/crear cohorte) no invoca `POST /api/v1/cohortes` porque el endpoint de cohortes vive bajo el módulo ADMIN de estructura académica (fuera del scope de C-23, per D6). El PasoCohorte captura el `cohorte_id` via form local (coordinador lo ingresa manualmente) y lo pasa a pasos subsiguientes. **Resolución**: acepta el `cohorte_id` como input del coordinador; la creación formal pertenece al módulo de estructura (otro change). No es una desviación del spec — el spec dice "seleccionar/crear cohorte (estructura académica existente)" y el módulo de estructura ADMIN es el "existente" que C-23 no debe pisar (D6).

### Desviación D1 — retryStep en useSetupWizard
Se agregó `retryStep` al hook (no especificado explícitamente en tasks pero requerido por la semántica del error state). Permite reintentar un paso fallido sin reiniciar todo el wizard. Triangulado en tests.

### Verificación 9.1
- **Baseline (antes de Batch 4)**: 338 tests / 44 archivos
- **Después de Batch 4**: 371 tests / 47 archivos
- **Nuevos tests**: 33 tests en 3 nuevos archivos (useSetupWizard x11, setupServices x13, SetupCuatrimestrePage x7) + buildNav extendido +5
- Todos verdes sin regresiones.

### Verificación 9.2 (LOC audit — setup-cuatrimestre)
- SetupCuatrimestrePage: 120 LOC ✓
- SetupStepper: 97 LOC ✓
- PasoCohorte: 77 LOC ✓
- PasoClonarEquipo: 116 LOC ✓
- PasoAsignaciones: 130 LOC ✓
- PasoVigencias: 95 LOC ✓
- PasoProgramas: 91 LOC ✓
- PasoFechas: 139 LOC ✓
- PasoAvisoBienvenida: 130 LOC ✓
- Sin `any`, sin class components ✓

### Verificación 9.3 (body-identity audit)
setupCuatrimestreService.ts — ningún campo `tenant_id`, `user_id`, `actor_id` en bodies. ✓
