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

### D5 — Atrasados: rutas con parámetros + `useQuery` por filtros (OQ-1 cerrada)
`materia_id` y `cohorte_id` llegan como **parámetros de URL** (`/materias/:materiaId/cohortes/:cohorteId/atrasados`). El usuario navega allí tras seleccionar una materia en la vista "mis-equipos" de C-23. `GET /analisis/atrasados` se modela con `useQuery({ queryKey: ['atrasados', materiaId, cohorteId, actividades], ... })` leyendo los params con `useParams()`. La paginación es client-side (el endpoint no pagina en servidor) — documentada como deuda técnica. La selección de alumnos (checkbox) vive en estado local y se pasa al formulario de comunicaciones como destinatarios.

### D6 — Comunicaciones: tres vistas, una máquina de estados (OQ-2 y OQ-4 cerradas)
(a) **Composición**: form RHF+Zod con `asunto_plantilla`, `cuerpo_plantilla`, destinatarios (precargados desde atrasados o manuales). **`variables_por_destinatario` es de solo lectura en esta entrega** (OQ-4): se construyen automáticamente desde `AlumnoAtrasado` (nombre, actividades faltantes) — la edición manual individual queda fuera de scope. Botón "Previsualizar" → `POST /preview`; botón "Encolar" → `POST /encolar` (201 → guarda `lote_id`). (b) **Bandeja de lote**: `useQuery(['lote', loteId])` sobre `GET /lote/{lote_id}` con contadores y `refetchInterval` acotado — **el estado `Enviando` es observable desde el backend** (OQ-2): el modelo de C-12 persiste la transición completa `Pendiente→Enviando→Enviado/Error/Cancelado`; el frontend lo lee directamente del endpoint. El `refetchInterval` se detiene cuando todos los mensajes alcanzan estado terminal. (c) **Aprobación**: mutations para aprobar/cancelar lote e individual; 409/404 se muestran como toast vía `sonner`. Governance MEDIO: checkpoints en el flujo de aprobación.

### D7 — Integración con el shell sin romper C-21
Editar solo dos puntos del shell: (1) el slot protegido de `App.tsx` para registrar `/padron`, `/atrasados`, `/comunicaciones` como rutas lazy envueltas en `ProtectedRoute requiredRoles={[...]}`; (2) `NAV_CATALOG` en `buildNav.ts` para agregar/ajustar los ítems. Los ítems de padrón/atrasados incluyen PROFESOR·TUTOR·COORDINADOR·ADMIN; el de comunicaciones ya existe (hoy COORDINADOR·ADMIN) y se amplía a PROFESOR·TUTOR porque `comunicacion:enviar` es del docente (FL-02 paso 7). El backend mantiene el fail-closed real; el front solo refleja visibilidad.

### D8 — Sistema de toasts: instalar `sonner` en el shell (OQ-3 cerrada)
C-21 **no tiene** sistema de toasts. C-22 introduce `sonner` (< 3 kB, React 18-native): instalar en `frontend/package.json`, agregar `<Toaster />` en `App.tsx` (una sola vez, a nivel global), y exportar `toast` de `sonner` para uso en hooks/componentes. Los errores 409/404 de comunicaciones y los éxitos de importación de padrón se notifican con toast. Los errores 422 (validación inline) se muestran en el form sin toast. Los errores 503 (Moodle no configurado) se muestran como aviso informativo en el componente, no como toast de error rojo.

## Risks / Trade-offs

- **[Paginación client-side de atrasados]** → El endpoint devuelve la lista completa; con comisiones grandes el render puede degradarse. Mitigación: paginar/virtualizar en cliente y dejar anotada la deuda para un endpoint paginado si el volumen lo exige.
- **[Avance del lote sin push real]** → Sin WebSockets, el usuario no ve transiciones en vivo. Mitigación: `refetchInterval` acotado mientras haya mensajes en Pendiente/Enviando, deteniéndolo cuando el lote llega a estado terminal.
- **[Origen de `materia_id`/`cohorte_id`]** → C-22 no define el catálogo de materias; si llega vacío, las vistas no pueden consultar. Mitigación: un selector simple basado en lo que exponga el contexto/API disponible, o parámetros de ruta, documentado como open question.
- **[Doble fuente de verdad de roles]** → El front decide visibilidad de nav/ruta, el backend decide autoridad. Riesgo de divergencia cosmética (un ítem visible que luego da 403). Mitigación: tratar el front como best-effort; el 403 del backend es la verdad y se muestra con `Forbidden403`/mensaje claro.
- **[Mapeo de estados Pendiente/Enviando]** → El backend expone `estado` como string del enum (`Pendiente`, `Enviado`, `Error`, `Cancelado`); "Enviando" es transitorio del worker. Mitigación: modelar la unión literal completa y tratar valores inesperados como estado desconocido sin romper el render.

## Open Questions

- **OQ-1** ✅ **CERRADA (2026-06-05)**: `materia_id`/`cohorte_id` como parámetros de URL (`/materias/:materiaId/cohortes/:cohorteId/atrasados`). El usuario navega desde la vista "mis-equipos" de C-23. Ver D5.
- **OQ-2** ✅ **CERRADA (2026-06-05)**: Estado `Enviando` observable desde el backend vía `GET /lote/{lote_id}`. C-12 persiste la transición completa. El frontend lee el estado directamente, no lo infiere. Ver D6.
- **OQ-3** ✅ **CERRADA (2026-06-05)**: C-21 no tiene toasts. C-22 instala `sonner` a nivel global en `App.tsx`. Ver D8.
- **OQ-4** ✅ **CERRADA (2026-06-05)**: `variables_por_destinatario` de solo lectura en esta entrega. Se construyen automáticamente desde `AlumnoAtrasado`; sin edición manual por alumno. Ver D6.
