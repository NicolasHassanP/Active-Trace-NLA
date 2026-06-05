## Context

C-22 monta la primera superficie de usuario del módulo académico-docente sobre tres APIs ya implementadas y estables:

- **Padrón (C-09)** — `/api/v1/padron`: `POST /preview` (multipart, devuelve `PadronRowDTO[]`, 422 si inválido), `POST /activar` (JSON `ActivarRequest`, 201 `VersionPadronRead`), `DELETE /vaciar?materia_id&cohorte_id` (204/404/403), `POST /sync-moodle` (JSON `SyncMoodleRequest`, 201 / 503 sin config / 502 indisponible). Permiso backend: `padron:cargar` (y `padron:gestionar` para vaciar versiones ajenas).
- **Análisis (C-11)** — `/api/v1/analisis`: `GET /atrasados?materia_id&cohorte_id&actividades` (devuelve `AlumnoAtrasado[]`), `GET /reporte-materia` (`ReporteMateria`), más ranking/notas-finales/monitor/export. Permiso: `atrasados:ver`. El scope (propio vs global) lo resuelve el grant del JWT en backend.
- **Comunicaciones (C-12)** — `/api/v1/comunicaciones`: `POST /preview` (`PreviewResponse`, 422 variable faltante), `POST /encolar` (201 `EncolarResponse`), `POST /aprobar-lote|cancelar-lote` (`ComunicacionRead[]`, 409 transición inválida), `POST /aprobar-individual|cancelar-individual` (`ComunicacionRead`, 404/409), `GET /lote/{lote_id}` (`LoteStatusResponse`). Permisos: `comunicacion:enviar` (preview/encolar/ver lote), `comunicacion:aprobar` (aprobar/cancelar).

El shell de C-21 ya provee: `apiClient` (Axios centralizado con interceptor de refresh, `frontend/src/shared/services/api.ts`), `tokenStore`, `useAuth` (expone `roles`, `isAuthenticated`), `ProtectedRoute` (acepta `requiredRoles`, fail-closed → 403), `AppLayout` con `<Outlet/>`, `NAV_CATALOG`/`buildNav`, y `QueryClientProvider` ya configurado (`retry: 1`, `staleTime: 5min`). Las rutas nuevas se montan en el slot protegido de `App.tsx`.

Constraints duras del proyecto: TypeScript sin `any`, sin class components, todo fetch vía TanStack Query (queries + mutations), forms con React Hook Form + Zod, Tailwind para estilos, componentes < 200 LOC, estructura feature-based `features/{name}/{components,hooks,services,types,pages}`. Identidad/tenant nunca viajan en body/URL — siempre del JWT, que el `apiClient` adjunta.

## Goals / Non-Goals

**Goals:**
- Vistas funcionales para los tres sub-dominios: importación de padrón, listado de atrasados, comunicaciones (composición + bandeja + aprobación).
- Reflejar fielmente los contratos y códigos de error del backend (422/502/503/409/404/403) con feedback claro al usuario.
- Reflejar la máquina de estados de comunicación: Pendiente → Enviando → OK/Fallido/Cancelado, con refetch del estado del lote.
- Guardar cada ruta con `ProtectedRoute` + roles, y registrar la navegación según rol.
- Aislar cada feature en su carpeta con la separación types → services → hooks → components/pages.

**Non-Goals:**
- No se modifica ninguna API de backend ni se agregan endpoints.
- No se implementa el wizard completo de importación de **calificaciones** (eso es de C-11/otra vista); C-22 cubre el padrón (alta de alumnos) y consume atrasados ya calculados.
- No se implementa polling en tiempo real con WebSockets — el avance del lote se observa con refetch on-demand / `refetchInterval` acotado.
- No se construyen selectores de materia/cohorte como catálogo nuevo: se asume que `materia_id`/`cohorte_id` llegan por contexto/ruta o un selector simple; el catálogo rico es responsabilidad de otra feature.
- No se cubre el módulo de avisos, inbox interno, encuentros ni coloquios (otros changes).

## Decisions

### D1 — Tres features independientes bajo `features/`
Crear `features/padron`, `features/atrasados`, `features/comunicaciones`, cada una con `types/`, `services/`, `hooks/`, `components/`, `pages/`. Alternativa considerada: una sola feature `academico` con submódulos. Rechazada porque las tres tienen permisos, rutas y ciclos de vida distintos, y el roadmap las trata como capabilities separadas. La separación mantiene los componentes < 200 LOC y los servicios testeables en aislamiento.

### D2 — Capa `services/` = funciones puras sobre `apiClient`; `hooks/` = TanStack Query
Igual que `authService.ts` + `useLogin.ts`: las funciones de `services/` envuelven los endpoints con tipos de request/response derivados de los schemas Pydantic, y los hooks (`useQuery`/`useMutation`) los consumen. Esto permite testear el service (mapeo de payload, manejo de error) sin React, y testear el hook con un `QueryClient` de test. Sin mocks de la lógica de negocio: los tests de service stubbean solo el transporte (`apiClient`).

### D3 — Tipos TS espejo de los schemas, en `snake_case` para el wire, `camelCase` para el dominio del front
Los DTOs de wire (lo que viaja en JSON) replican exactamente los nombres del backend (`materia_id`, `entrada_padron_id`, `lote_id`, `asunto_plantilla`) para evitar transformaciones frágiles. Donde el front modela estado propio (formularios), se usa `camelCase` y se mapea en el borde del service. Nunca `any`: uniones literales para estados (`'Pendiente' | 'Enviando' | 'Enviado' | 'Fallido' | 'Cancelado'`) y `'atrasado' | 'al_dia' | 'sin_datos'`.

### D4 — Importación de padrón en dos pasos: preview → activar
El flujo de UI sigue el contrato: el usuario sube un archivo → `POST /preview` (multipart `FormData`) → se muestran las filas detectadas → el usuario confirma → `POST /activar` con esas mismas filas + `materia_id`/`cohorte_id`. El preview es una `mutation` (no query: tiene efecto de parseo y entrada del usuario). 422 del preview → mensaje de archivo inválido con el `detail` del backend. Sync Moodle es una `mutation` separada con manejo explícito de 503 (no configurado → aviso informativo, no error rojo) y 502 (indisponible → reintentable).

### D5 — Atrasados como `useQuery` con `queryKey` por filtros; selección de filas en estado local
`GET /analisis/atrasados` se modela con `useQuery({ queryKey: ['atrasados', materiaId, cohorteId, actividades], ... })`. La paginación es client-side sobre el array devuelto (el endpoint no paginа en servidor) — se documenta como decisión y como posible deuda si los volúmenes crecen. La selección de alumnos (checkbox) vive en estado local del componente y se pasa al formulario de comunicaciones como destinatarios (emails de `AlumnoAtrasado.email`). El `reporte-materia` se consulta en paralelo como encabezado de métricas.

### D6 — Comunicaciones: tres vistas, una máquina de estados
(a) **Composición**: form RHF+Zod con `asunto_plantilla`, `cuerpo_plantilla`, destinatarios (precargados desde atrasados o manuales) y variables por destinatario; botón "Previsualizar" → `POST /preview`; botón "Encolar" → `POST /encolar` (201 → guarda `lote_id`). (b) **Bandeja de lote**: `useQuery(['lote', loteId])` sobre `GET /lote/{lote_id}` con contadores (pendientes/enviados/errores/cancelados) y refetch para observar el avance Pendiente→Enviando→OK/Fallido. (c) **Aprobación**: mutations para aprobar/cancelar lote e individual, con invalidación de la query del lote tras cada acción; 409 (transición inválida) y 404 se muestran como toast/error de fila sin romper la vista. Governance MEDIO: el flujo de aprobación se implementa con checkpoints y se surfacean las decisiones de UX de confirmación.

### D7 — Integración con el shell sin romper C-21
Editar solo dos puntos del shell: (1) el slot protegido de `App.tsx` para registrar `/padron`, `/atrasados`, `/comunicaciones` como rutas lazy envueltas en `ProtectedRoute requiredRoles={[...]}`; (2) `NAV_CATALOG` en `buildNav.ts` para agregar/ajustar los ítems. Los ítems de padrón/atrasados incluyen PROFESOR·TUTOR·COORDINADOR·ADMIN; el de comunicaciones ya existe (hoy COORDINADOR·ADMIN) y se amplía a PROFESOR·TUTOR porque `comunicacion:enviar` es del docente (FL-02 paso 7). El backend mantiene el fail-closed real; el front solo refleja visibilidad.

### D8 — Manejo de errores centralizado por feature
Cada service traduce los códigos HTTP del backend a un tipo de error de dominio (`PadronError`, `ComunicacionError`) con `status` y `detail`, para que los componentes decidan la presentación (422 inline, 503 informativo, 409/404 toast). Se reutiliza el manejo de Axios del `apiClient`; no se agrega librería de toasts nueva salvo que ya exista en el shell.

## Risks / Trade-offs

- **[Paginación client-side de atrasados]** → El endpoint devuelve la lista completa; con comisiones grandes el render puede degradarse. Mitigación: paginar/virtualizar en cliente y dejar anotada la deuda para un endpoint paginado si el volumen lo exige.
- **[Avance del lote sin push real]** → Sin WebSockets, el usuario no ve transiciones en vivo. Mitigación: `refetchInterval` acotado mientras haya mensajes en Pendiente/Enviando, deteniéndolo cuando el lote llega a estado terminal.
- **[Origen de `materia_id`/`cohorte_id`]** → C-22 no define el catálogo de materias; si llega vacío, las vistas no pueden consultar. Mitigación: un selector simple basado en lo que exponga el contexto/API disponible, o parámetros de ruta, documentado como open question.
- **[Doble fuente de verdad de roles]** → El front decide visibilidad de nav/ruta, el backend decide autoridad. Riesgo de divergencia cosmética (un ítem visible que luego da 403). Mitigación: tratar el front como best-effort; el 403 del backend es la verdad y se muestra con `Forbidden403`/mensaje claro.
- **[Mapeo de estados Pendiente/Enviando]** → El backend expone `estado` como string del enum (`Pendiente`, `Enviado`, `Error`, `Cancelado`); "Enviando" es transitorio del worker. Mitigación: modelar la unión literal completa y tratar valores inesperados como estado desconocido sin romper el render.

## Open Questions

- **OQ-1 (contrato real de selección de materia/cohorte)**: ¿de dónde toma el front `materia_id`/`cohorte_id`? ¿Hay un endpoint de "mis materias" para el docente (C-23) o C-22 usa un input manual/parámetro de ruta provisional? Resolver antes de cablear las queries.
- **OQ-2 (estado "Enviando")**: el enum de backend parece exponer `Pendiente|Enviado|Error|Cancelado`; ¿existe un valor intermedio `Enviando` observable vía `GET /lote`, o el front lo infiere? Confirmar contra el modelo `ComunicacionEstado`.
- **OQ-3 (toasts/notificaciones)**: ¿el shell de C-21 ya provee un sistema de toasts reutilizable, o C-22 introduce uno mínimo? Evitar duplicar.
- **OQ-4 (variables por destinatario en la UI)**: `encolar` acepta `variables_por_destinatario` (dict email → vars). ¿La UI de C-22 expone edición de variables por alumno, o usa solo variables comunes derivadas de `AlumnoAtrasado` (nombre, actividades faltantes)? Acordar alcance de la primera entrega.
