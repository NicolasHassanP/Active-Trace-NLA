## Why

El backend de mensajería interna se implementó completo en C-20 (`/api/v1/inbox`: listar hilos, abrir hilo, iniciar hilo, responder), pero nunca recibió su frontend. La ruta `/mensajes` no existe en el router de React y el ítem de nav previsto lleva a 404. Los usuarios del sistema (PROFESOR, TUTOR, COORDINADOR, ADMIN) no tienen forma de usar la bandeja desde la UI. C-26 cierra esa brecha consumiendo los endpoints existentes — es exclusivamente trabajo de frontend.

## What Changes

- Nueva feature `features/mensajeria/` con estructura feature-based (`components`, `hooks`, `services`, `types`, `pages`).
- Nueva página `InboxPage` montada en la ruta protegida `/mensajes`.
- Lista de hilos: asunto del hilo, contador de no leídos, timestamp del último mensaje.
- Vista de hilo individual: mensajes en orden cronológico con remitente y cuerpo; al abrir, el backend marca leído.
- Formulario para iniciar un hilo nuevo (destinatario, asunto, cuerpo) con React Hook Form + Zod.
- Formulario para responder dentro de un hilo (asunto, cuerpo) con React Hook Form + Zod.
- Service tipado que envuelve los 4 endpoints de `/api/v1/inbox` vía el cliente Axios centralizado.
- Hooks de TanStack Query (queries para listar/abrir, mutations para iniciar/responder con invalidación de caché).
- Nuevo ítem en el catálogo de nav: label "Mensajes", ícono `mail`, group `TRABAJO`, visible para PROFESOR, TUTOR, COORDINADOR, ADMIN.
- Registro de la ruta `/mensajes` en `App.tsx` (lazy, dentro del slot protegido, gateada por roles).

Sin cambios de backend. Sin cambios de contrato de API.

## Capabilities

### New Capabilities
- `mensajeria-frontend`: UI de bandeja de mensajería interna — listado de hilos, vista de hilo cronológica, iniciar hilo y responder, consumiendo los endpoints existentes de `/api/v1/inbox`; navegación y RBAC del ítem de nav.

### Modified Capabilities
<!-- Ninguna. El backend (C-20) ya está cerrado y su contrato no cambia. -->

## Impact

- **Frontend (nuevo)**: `frontend/src/features/mensajeria/{types,services,hooks,components,pages}`.
- **Frontend (modificado)**: `frontend/src/features/shell/components/buildNav.ts` (nuevo ítem de nav), `frontend/src/App.tsx` (nueva ruta lazy `/mensajes`).
- **Backend**: sin cambios — consume `backend/app/api/v1/routers/inbox.py` tal como está.
- **Permiso backend**: los endpoints exigen `inbox:usar` (fail-closed → 403). El frontend gatea la visibilidad por rol; el backend sigue siendo la autoridad.
- **Dependencias**: C-20 (backend mensajería) y C-21 (shell + auth) archivados; C-23 como referencia de estructura. Sin bloqueadores.
