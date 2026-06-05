## Why

El backend del módulo académico-docente ya está completo (C-09 padrón, C-11 análisis/atrasados, C-12 comunicaciones) y el shell del frontend ya existe (C-21: `AppLayout`, `ProtectedRoute`, `useAuth`, cliente Axios). Hoy esas APIs no tienen ninguna superficie de usuario: PROFESOR, TUTOR y COORDINADOR no pueden importar el padrón, ver alumnos atrasados ni enviar comunicaciones desde la interfaz. C-22 entrega las vistas React que cierran el flujo central del producto (FL-02 + FL-04): importar → analizar → comunicar.

## What Changes

- **Feature `padron`**: vista para importar el padrón de una materia×cohorte. Preview de filas (multipart upload a `POST /padron/preview`), confirmación (`POST /padron/activar`), sincronización on-demand desde Moodle (`POST /padron/sync-moodle`) y vaciado del padrón activo (`DELETE /padron/vaciar`). Manejo explícito de los estados 422 (archivo inválido), 503 (Moodle no configurado) y 502 (Moodle no disponible).
- **Feature `atrasados`**: tabla paginada de alumnos atrasados por materia×cohorte×actividades (`GET /analisis/atrasados`), con filtros y selección de filas para alimentar el flujo de comunicaciones. Lectura del reporte de materia (`GET /analisis/reporte-materia`) como encabezado de métricas.
- **Feature `comunicaciones`**: bandeja de estado de un lote (`GET /comunicaciones/lote/{lote_id}`), formulario de nueva comunicación con preview de plantilla (`POST /comunicaciones/preview`) y encolado (`POST /comunicaciones/encolar`), y panel de aprobación que aprueba/cancela el lote completo o mensajes individuales (`POST /comunicaciones/aprobar-lote|cancelar-lote|aprobar-individual|cancelar-individual`). Refleja la máquina de estados Pendiente → Enviando → OK/Fallido/Cancelado.
- **Integración con el shell**: registro de las rutas nuevas en el slot protegido de `App.tsx`, cada una envuelta en `ProtectedRoute` con sus roles requeridos; alta de los ítems de navegación en `NAV_CATALOG`.

No hay cambios de backend. No hay breaking changes.

## Capabilities

### New Capabilities
- `padron-importacion`: superficie de usuario para previsualizar, activar, sincronizar y vaciar el padrón de una materia×cohorte, con feedback de progreso y de los códigos de error del backend.
- `atrasados`: listado filtrable y paginable de alumnos atrasados por materia×cohorte, con métricas de reporte y selección para comunicar.
- `comunicaciones-frontend`: composición de comunicaciones salientes con preview de plantilla, encolado, bandeja de estado de lote y panel de aprobación/cancelación (lote e individual).

### Modified Capabilities
<!-- Ninguna. C-22 solo consume APIs existentes; no altera requerimientos de capabilities ya especificadas. -->

## Impact

- **Frontend**: nuevos directorios `frontend/src/features/{padron,atrasados,comunicaciones}/{types,services,hooks,components,pages}`.
- **Shell**: edición de `frontend/src/App.tsx` (rutas en el slot protegido) y `frontend/src/features/shell/components/buildNav.ts` (ítems de navegación). Ajuste menor de `NAV_CATALOG` para que el ítem "Comunicaciones" y los nuevos ítems "Padrón" / "Atrasados" incluyan los roles PROFESOR y TUTOR donde corresponda.
- **APIs consumidas**: `/api/v1/padron/*` (C-09), `/api/v1/analisis/*` (C-11), `/api/v1/comunicaciones/*` (C-12). Sin cambios de contrato.
- **Permisos / roles**: rutas guardadas por `ProtectedRoute` con roles PROFESOR · TUTOR · COORDINADOR · ADMIN según corresponda. El backend mantiene el fail-closed de RBAC fino (`padron:cargar`, `atrasados:ver`, `comunicacion:enviar`, `comunicacion:aprobar`); el frontend solo refleja el acceso, nunca decide autoridad.
- **Dependencias npm**: ninguna nueva — TanStack Query, React Hook Form, Zod, Axios y Tailwind ya están instalados.
