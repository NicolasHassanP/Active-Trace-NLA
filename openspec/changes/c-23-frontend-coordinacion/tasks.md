# Tasks — C-23 frontend-coordinacion

> Strict TDD: para cada tarea con lógica (service/hook/validación), escribir el test que falla ANTES del código.
> Cada módulo replica la estructura de C-22 (`types/index.ts`, `services/<name>Service.ts`, `hooks/<name>Hooks.ts`, `components/*`, `pages/*`, `__tests__`).
> Todos los services envuelven errores con `parseDomainError`. Todo fetch pasa por hooks de TanStack Query.
> Resolver OQ-1..OQ-5 (design.md) antes de las tareas que dependen de ellas.

## 0. Preparación (resolver antes de implementar)

- [ ] 0.1 Resolver OQ-1 (lectura de avisos para gestión), OQ-3 (export del monitor), OQ-4 (filtros de encuentros/guardias) con el usuario/profesor
- [ ] 0.2 Leer schemas backend exactos: `backend/app/schemas/{equipo,aviso,tarea}.py` y los DTOs de coloquios/encuentros/guardias/monitor para alinear `types` (OQ-2)
- [ ] 0.3 Decidir ubicación del helper de descarga de blobs (OQ-5): crear `@/shared/services/downloadFile.ts` si no existe en C-22

## 1. Equipos (`features/equipos`)

- [ ] 1.1 Definir `types/index.ts` (MisEquiposItem, ResumenLote, ResumenClonacion, requests) alineados al schema backend
- [ ] 1.2 TDD `equiposService.listarMisEquipos` → `GET /api/v1/equipos/mis-equipos` (happy path + error)
- [ ] 1.3 TDD `equiposService.consultarEquipo` → `GET /api/v1/equipos` con tripleta + filtros opcionales
- [ ] 1.4 TDD `equiposService.asignacionMasiva` → `POST /api/v1/equipos/asignacion-masiva` (201 + 422)
- [ ] 1.5 TDD `equiposService.clonarEquipo` → `POST /api/v1/equipos/clonar`
- [ ] 1.6 TDD `equiposService.vigenciaGeneral` → `PATCH /api/v1/equipos/vigencia-general`
- [ ] 1.7 TDD `equiposService.exportarEquipo` → `GET /api/v1/equipos/exportar` (blob + descarga)
- [ ] 1.8 TDD hooks (`useMisEquipos`, `useEquipo`, mutations) con queryKey por filtros e invalidación
- [ ] 1.9 Componentes: `MisEquiposTable`, `EquipoFilters`, `AsignacionMasivaForm` (RHF+Zod), `ClonarEquipoDialog`, `VigenciaGeneralForm` (cada uno < 200 LOC)
- [ ] 1.10 TDD `EquiposPage`: render por rol (gestión COORDINADOR/ADMIN vs solo mis-equipos PROFESOR), estados vacío/error

## 2. Avisos (`features/avisos`)

- [ ] 2.1 Definir `types/index.ts` (AvisoRead, CrearAvisoRequest, ActualizarAvisoRequest, AcknowledgmentRead, enums de alcance/severidad)
- [ ] 2.2 TDD `avisosService` gestión: crear `POST /api/v1/avisos` (201), editar `PUT /{id}` (200/404), baja `DELETE /{id}` (204/404)
- [ ] 2.3 TDD `avisosService` feed: `GET /api/v1/avisos` y `GET /api/v1/avisos/pendientes`
- [ ] 2.4 TDD `avisosService.ack` → `POST /api/v1/avisos/{id}/ack` (200/403/404)
- [ ] 2.5 TDD Zod schema del aviso: alcance no global ⇒ contexto (materia/cohorte) obligatorio
- [ ] 2.6 TDD hooks (lista, pendientes, mutations de gestión y ack) con invalidación
- [ ] 2.7 Componentes: `AvisoForm` (RHF+Zod), `AvisosTable`, `BandejaAvisos`, `AckButton`
- [ ] 2.8 TDD `AvisosPage`: gestión visible solo COORDINADOR/ADMIN; bandeja para cualquier autenticado

## 3. Tareas (`features/tareas`)

- [ ] 3.1 Definir `types/index.ts` (TareaRead, ComentarioTareaRead, requests, estados del workflow)
- [ ] 3.2 TDD `tareasService`: `GET /tareas/mias`, `GET /tareas/{id}`, `GET /tareas/admin` (con filtros)
- [ ] 3.3 TDD `tareasService`: `POST /tareas` (alta), `POST /tareas/{id}/delegar`
- [ ] 3.4 TDD `tareasService`: `PATCH /tareas/{id}/estado`, comentarios `GET`/`POST /tareas/{id}/comentarios`
- [ ] 3.5 TDD Zod schema de alta de tarea (docente asignado y descripción obligatorios)
- [ ] 3.6 TDD hooks (mis-tareas, admin con filtros, detalle, mutations) con invalidación
- [ ] 3.7 Componentes: `MisTareasList`, `TareasAdminTable`, `TareasFilters`, `TareaForm`, `EstadoSelector`, `ComentariosThread`
- [ ] 3.8 TDD `TareasPage`: mis-tareas para todos los roles habilitados; panel admin solo COORDINADOR/ADMIN

## 4. Monitores (`features/monitores`)

- [ ] 4.1 Definir `types/index.ts` (MonitorFila, params de filtro)
- [ ] 4.2 TDD `monitoresService.listarMonitor` → `GET /api/v1/analisis/monitor` con todos los filtros (materia, regional, comisión, búsqueda, estado, clasificación, rango de fechas)
- [ ] 4.3 TDD `monitoresService.exportar` (según OQ-3: endpoint dedicado, reutilizado o client-side)
- [ ] 4.4 TDD hook `useMonitor` con queryKey que incluye TODOS los filtros activos
- [ ] 4.5 Componentes: `MonitorFilters`, `MonitorTable`, `MonitorToolbar` (limpiar/exportar)
- [ ] 4.6 TDD `MonitorPage`: gating COORDINADOR/ADMIN, filtros aplicados/limpiados, estado vacío

## 5. Encuentros coordinación + guardias (`features/encuentros-coord`)

- [ ] 5.1 Definir `types/index.ts` (InstanciaEncuentroRead, GuardiaRead, params de filtro — OQ-4)
- [ ] 5.2 TDD `encuentrosCoordService.listarInstancias` → `GET /api/v1/encuentros/instancias`
- [ ] 5.3 TDD `encuentrosCoordService.listarGuardias` → `GET /api/v1/guardias`
- [ ] 5.4 TDD `encuentrosCoordService.exportarGuardias` → `GET /api/v1/guardias/export` (blob + descarga)
- [ ] 5.5 TDD hooks (instancias, guardias) con filtros en queryKey
- [ ] 5.6 Componentes: `InstanciasEncuentroTable`, `GuardiasTable`, `GuardiasFilters`
- [ ] 5.7 TDD `EncuentrosPage`: gating COORDINADOR/ADMIN, vista transversal y registro de guardias

## 6. Coloquios (`features/coloquios`)

- [ ] 6.1 Definir `types/index.ts` (MetricasRead, ConvocatoriaMetricasRead, ConvocatoriaConTurnosRead, AgendaItemRead, ResultadoRead, requests)
- [ ] 6.2 TDD `coloquiosService.metricas` → `GET /api/v1/coloquios/metricas`
- [ ] 6.3 TDD `coloquiosService.listarConvocatorias` → `GET /api/v1/coloquios/convocatorias`
- [ ] 6.4 TDD `coloquiosService.crearConvocatoria` → `POST /api/v1/coloquios/convocatorias` (201)
- [ ] 6.5 TDD `coloquiosService.importarCandidatos` → `POST /api/v1/coloquios/convocatorias/{id}/candidatos` (204)
- [ ] 6.6 TDD `coloquiosService.cerrarConvocatoria` → `POST /api/v1/coloquios/convocatorias/{id}/cerrar`
- [ ] 6.7 TDD `coloquiosService.agenda` → `GET /api/v1/coloquios/agenda`; `resultados` → `GET /api/v1/coloquios/convocatorias/{id}/resultados`
- [ ] 6.8 TDD Zod schema de convocatoria (cupo > 0, días disponibles presentes)
- [ ] 6.9 TDD hooks (métricas, convocatorias, mutations, agenda, resultados) con invalidación
- [ ] 6.10 Componentes: `MetricasPanel`, `ConvocatoriasTable`, `ConvocatoriaForm`, `ImportarCandidatosDialog`, `AgendaReservas`, `ResultadosTable`
- [ ] 6.11 TDD `ColoquiosPage`: gating COORDINADOR/ADMIN, métricas + convocatorias + acciones

## 7. Setup de cuatrimestre (`features/setup-cuatrimestre`)

- [ ] 7.1 Definir `types/index.ts` (estado del wizard, pasos, estado por paso)
- [ ] 7.2 TDD `useSetupWizard` (estado del flujo: pasos pendiente/completado, avance condicionado)
- [ ] 7.3 Componente `SetupStepper` (lista de pasos con estado) < 200 LOC
- [ ] 7.4 Paso 1: seleccionar/crear cohorte (reusa estructura académica existente)
- [ ] 7.5 Paso 2: clonar equipo (reusa `equiposService.clonarEquipo`)
- [ ] 7.6 Paso 3: ajustar asignaciones (reusa `equiposService.asignacionMasiva`)
- [ ] 7.7 Paso 4: ajustar vigencias (reusa `equiposService.vigenciaGeneral`)
- [ ] 7.8 Paso 5: cargar programas → `POST /api/v1/programas` (service + Zod)
- [ ] 7.9 Paso 6: cargar fechas de evaluaciones → `POST /api/v1/fechas-academicas` (service + Zod)
- [ ] 7.10 Paso 7: publicar aviso de bienvenida (reusa `avisosService.crear`)
- [ ] 7.11 TDD `SetupCuatrimestrePage`: gating COORDINADOR/ADMIN, avance secuencial, error no avanza, completado

## 8. Routing y navegación (integración)

- [ ] 8.1 Registrar rutas lazy en `App.tsx`: `/equipos`, `/avisos`, `/tareas`, `/monitor`, `/encuentros`, `/coloquios`, `/setup-cuatrimestre`, cada una con `ProtectedRoute requiredRoles` según matriz RBAC
- [ ] 8.2 Activar/añadir ítems en `buildNav.ts`: `/avisos`, `/tareas`, `/monitor`, `/setup-cuatrimestre` (gateados por rol); confirmar `/equipos`, `/encuentros`, `/coloquios` ya presentes
- [ ] 8.3 TDD `buildNav`: un COORDINADOR ve los ítems de coordinación; un PROFESOR/FINANZAS no ve los exclusivos de COORDINADOR/ADMIN

## 9. Verificación final

- [ ] 9.1 Correr `vitest` completo del frontend — todos los tests verdes
- [ ] 9.2 Verificar que ningún componente supere 200 LOC y que no haya `any` ni class components
- [ ] 9.3 Verificar que ningún service envía identidad/tenant en el body
- [ ] 9.4 Marcar tareas completas y registrar desviaciones / OQ resueltas
