## 1. Tipos y contrato

- [ ] 1.1 Crear `features/mensajeria/types/index.ts` con `InboxHiloRead`, `MensajeRead`, `HiloCreate` (request) y `RespuestaCreate` (request) espejando los schemas de `backend/app/schemas/mensajeria.py` (snake_case, sin `any`)

## 2. Service

- [ ] 2.1 Crear `features/mensajeria/services/mensajeriaService.ts` con `listarHilos()` → `GET /inbox` usando `apiClient` y `parseDomainError`
- [ ] 2.2 Agregar `abrirHilo(hiloId)` → `GET /inbox/{hilo_id}` (devuelve `MensajeRead[]`)
- [ ] 2.3 Agregar `iniciarHilo(body: HiloCreate)` → `POST /inbox` (devuelve `MensajeRead`); identidad/tenant nunca en el body
- [ ] 2.4 Agregar `responder(hiloId, body: RespuestaCreate)` → `POST /inbox/{hilo_id}/responder` (devuelve `MensajeRead`)
- [ ] 2.5 Definir los Zod schemas `nuevoHiloSchema` (`destinatario_id` requerido, `asunto?`, `cuerpo` no vacío) y `responderSchema` (`asunto` no vacío, `cuerpo` no vacío) con sus tipos inferidos

## 3. Hooks de TanStack Query

- [ ] 3.1 Crear `features/mensajeria/hooks/mensajeriaHooks.ts` con `useHilos()` (queryKey `['mensajeria-hilos']`)
- [ ] 3.2 Agregar `useHilo(hiloId)` (queryKey `['mensajeria-hilo', hiloId]`, `enabled: !!hiloId`)
- [ ] 3.3 Agregar `useIniciarHilo()` (mutation; invalida `['mensajeria-hilos']` on success)
- [ ] 3.4 Agregar `useResponder()` (mutation; invalida `['mensajeria-hilo', hiloId]` y `['mensajeria-hilos']` on success)

## 4. Componentes

- [ ] 4.1 Crear `components/HilosList.tsx`: lista de hilos con asunto (o "(sin asunto)"), badge de no leídos y `ultimo_mensaje_at`; estado vacío con `EmptyState`; emite `onSelect(hiloId)` (< 200 LOC)
- [ ] 4.2 Crear `components/HiloView.tsx`: mensajes en orden cronológico (cuerpo, `created_at`), distinción de mensajes propios vía `remitente_id === currentUserId` (id desde `useAuth`) (< 200 LOC)
- [ ] 4.3 Crear `components/NuevoHiloForm.tsx`: React Hook Form + `nuevoHiloSchema`; on submit llama `useIniciarHilo`; maneja errores 404/409 de dominio (< 200 LOC)
- [ ] 4.4 Crear `components/ResponderForm.tsx`: React Hook Form + `responderSchema`; on submit llama `useResponder` para el hilo abierto (< 200 LOC)

## 5. Página

- [ ] 5.1 Crear `features/mensajeria/pages/InboxPage.tsx`: layout master-detail con `useState` para `selectedHiloId`, compone `HilosList` + `HiloView` + `NuevoHiloForm` + `ResponderForm`, usa `PageHeader`, sin `max-w-*`/`mx-auto` en el wrapper raíz, gatea por rol con `useAuth` (< 200 LOC)

## 6. Navegación y ruteo

- [ ] 6.1 Agregar a `NAV_CATALOG` en `features/shell/components/buildNav.ts` el ítem `{ label: 'Mensajes', path: '/mensajes', roles: ['PROFESOR','TUTOR','COORDINADOR','ADMIN'], icon: 'mail', group: 'TRABAJO' }`
- [ ] 6.2 Verificar que el ícono `mail` esté soportado por `NavIcon` (ya usado por "Comunicaciones"); agregarlo si falta
- [ ] 6.3 Registrar en `App.tsx` la página lazy `InboxPage` y la ruta protegida `/mensajes` con `requiredRoles` PROFESOR/TUTOR/COORDINADOR/ADMIN

## 7. Tests (Strict TDD)

- [ ] 7.1 Tests del service: cada función llama al endpoint correcto vía `apiClient` y no incluye identidad/tenant en el body
- [ ] 7.2 Tests de los Zod schemas: rechazan `cuerpo`/`asunto` vacíos; aceptan payloads válidos
- [ ] 7.3 Test de `buildNav`: "Mensajes" visible para COORDINADOR, oculto para ALUMNO
- [ ] 7.4 Tests de componentes/página: render de lista, estado vacío, apertura de hilo, distinción de mensaje propio, submit de nuevo hilo y de respuesta, manejo de errores 404/409
