## 1. Andamiaje y tipos compartidos

- [ ] 1.1 Instalar `sonner` en `frontend/package.json`; agregar `<Toaster />` en `App.tsx` a nivel global (OQ-3 cerrada — C-21 no tiene toasts)
- [ ] 1.2 Crear la estructura de carpetas `features/padron`, `features/atrasados`, `features/comunicaciones` con subcarpetas `types/`, `services/`, `hooks/`, `components/`, `pages/`
- [ ] 1.3 Definir un tipo/helper de error de dominio reutilizable que extraiga `status` y `detail` de un `AxiosError` (sin `any`), usado por los tres services para traducir 422/502/503/409/404/403

## 2. Padrón — tipos y service (BAJO, con test)

- [ ] 2.1 Definir tipos wire en `features/padron/types`: `PadronRowDTO`, `ActivarRequest`, `VersionPadronRead`, `SyncMoodleRequest` (espejo de los schemas de C-09)
- [ ] 2.2 RED: test de `padronService.preview` — stub del transporte; verifica multipart `FormData` y mapeo de 200 → filas; 422 → error de dominio con `detail`
- [ ] 2.3 GREEN/TRIANGULATE: implementar `padronService.preview`, `activar`, `vaciar`, `syncMoodle` con casos de 201, 204, 404, 403, 503, 502
- [ ] 2.4 Test de `padronService.activar`: el cuerpo enviado contiene solo `materia_id`, `cohorte_id`, `rows` (sin identidad ni tenant)

## 3. Padrón — hooks y vista (BAJO, con test)

- [ ] 3.1 RED/GREEN: hooks TanStack Query `usePreviewPadron`, `useActivarPadron`, `useVaciarPadron`, `useSyncMoodlePadron` (mutations) con `QueryClient` de test
- [ ] 3.2 Componente `PadronImportForm` (< 200 LOC): upload de archivo → preview → tabla de filas → confirmar, con manejo de 422 inline
- [ ] 3.3 Componente `SyncMoodlePanel` (< 200 LOC): dispara sync; 503 → aviso informativo, 502 → error reintentable, 201 → éxito con total de filas
- [ ] 3.4 Componente de vaciado con confirmación previa; manejo de 204/404/403
- [ ] 3.5 `PadronPage` que compone selector de materia/cohorte + import + sync + vaciado; tests de render por estado (éxito, 422, 503)

## 4. Atrasados — tipos y service (BAJO, con test)

- [ ] 4.1 Definir tipos wire en `features/atrasados/types`: `AlumnoAtrasado`, `ReporteMateria` (espejo de los schemas de C-11), con uniones literales sin `any`
- [ ] 4.2 RED/GREEN/TRIANGULATE: `atrasadosService.listarAtrasados` (query params `materia_id`, `cohorte_id`, `actividades[]`) y `atrasadosService.reporteMateria`; casos 200 con lista, lista vacía, y `sin_datos`

## 5. Atrasados — hooks y vista (BAJO, con test)

- [ ] 5.1 RED/GREEN: `useAtrasados` y `useReporteMateria` con `queryKey` que incluye los filtros activos
- [ ] 5.2 Componente `AtrasadosTable` (< 200 LOC): tabla con `actividades_faltantes`/`actividades_no_aprobadas`, estado vacío, y paginación client-side
- [ ] 5.3 Ruta `/materias/:materiaId/cohortes/:cohorteId/atrasados` — leer `materiaId`/`cohorteId` con `useParams()` y pasarlos al `queryKey` (OQ-1); componente `AtrasadosFilters` para filtro de `actividades[]`
- [ ] 5.4 Componente `ReporteMateriaHeader` (< 200 LOC): métricas (total alumnos, atrasados, tasa) con manejo de `sin_datos`
- [ ] 5.5 Selección de alumnos (checkbox) en estado local que habilita "Comunicar a seleccionados" y propaga los emails; test de habilitación/deshabilitación
- [ ] 5.6 `AtrasadosPage` que compone filtros + header + tabla + acción de comunicar; tests de render por estado

## 6. Comunicaciones — tipos y service (MEDIO, con test)

- [ ] 6.1 Definir tipos wire en `features/comunicaciones/types`: `PreviewRequest/Response`, `EncolarRequest/Response`, `LoteRequest`, `IndividualRequest`, `LoteStatusResponse`, `ComunicacionRead` con unión literal de `estado` (`Pendiente|Enviando|Enviado|Fallido|Cancelado`)
- [ ] 6.2 RED: test de `comunicacionService.preview` (200 render, 422 variable faltante) y `encolar` (201 con `lote_id`, 422)
- [ ] 6.3 GREEN/TRIANGULATE: implementar `preview`, `encolar`, `getLote`, `aprobarLote`, `cancelarLote`, `aprobarIndividual`, `cancelarIndividual` con casos 200/201/404/409
- [ ] 6.4 Test: el cuerpo de `encolar` no incluye identidad ni tenant del remitente

## 7. Comunicaciones — hooks (MEDIO, con test)

- [ ] 7.1 RED/GREEN: mutations `usePreviewComunicacion`, `useEncolarLote`, `useAprobarLote`, `useCancelarLote`, `useAprobarIndividual`, `useCancelarIndividual` con invalidación de la query del lote
- [ ] 7.2 RED/GREEN: `useLoteStatus` (query) con `refetchInterval` activo solo mientras haya mensajes `Pendiente`/`Enviando` (estado observable directamente del backend — OQ-2); detenido cuando todos los mensajes son terminales (`Enviado`/`Error`/`Cancelado`)

## 8. Comunicaciones — vistas (MEDIO, con test)

- [ ] 8.1 Schema Zod + form `ComposeComunicacion` (RHF, < 200 LOC): `asunto_plantilla`, `cuerpo_plantilla`, destinatarios; `variables_por_destinatario` construidas automáticamente desde `AlumnoAtrasado` (solo lectura, sin edición manual por alumno — OQ-4); validación de campos vacíos/sin destinatarios
- [ ] 8.2 Preview de plantilla en el form: 200 muestra render, 422 muestra variable faltante y bloquea encolar; test de ambos caminos
- [ ] 8.3 Encolar → retiene `lote_id` y abre la bandeja; test de éxito y de 422
- [ ] 8.4 Componente `LoteStatusBandeja` (< 200 LOC): contadores (pendientes/enviados/errores/cancelados) + detalle por mensaje; test de refresco mientras hay mensajes en curso
- [ ] 8.5 Componente `AprobacionPanel` (< 200 LOC): aprobar/cancelar lote e individual; manejo de 409 sin romper vista y 404 por fila; visible solo para roles con `comunicacion:aprobar`
- [ ] 8.6 `ComunicacionesPage` que compone composición + bandeja + aprobación, precargando destinatarios provenientes de atrasados; tests de render por estado

## 9. Integración con el shell

- [ ] 9.1 Registrar `/padron`, `/atrasados`, `/comunicaciones` como rutas lazy en el slot protegido de `App.tsx`, cada una envuelta en `ProtectedRoute` con sus `requiredRoles`
- [ ] 9.2 Actualizar `NAV_CATALOG` en `buildNav.ts`: agregar ítems "Padrón" y "Atrasados" (PROFESOR·TUTOR·COORDINADOR·ADMIN) y ampliar "Comunicaciones" a PROFESOR·TUTOR; actualizar test `buildNav.test.ts`
- [ ] 9.3 Test de integración de ruteo: acceso permitido renderiza la página, rol no autorizado obtiene 403 (fail-closed)

## 10. Verificación final

- [ ] 10.1 Ejecutar la suite de tests del frontend y confirmar verde sin romper tests de C-21
- [ ] 10.2 Verificar que ningún archivo nuevo usa `any`, ningún componente supera 200 LOC, y todos los componentes son funcionales
- [ ] 10.3 Confirmar que las 4 OQs están implementadas: rutas con params (OQ-1), polling sobre estado real del backend (OQ-2), `sonner` integrado (OQ-3), variables read-only (OQ-4)
