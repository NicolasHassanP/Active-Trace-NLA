# Handoff — rama `style/design-handoff`

> Documento generado al finalizar la sesión de diseño. Contiene todo el contexto
> necesario para continuar sin perder información. Leé esto ANTES de tocar cualquier
> archivo del frontend.

---

## 1. Qué es esta rama

`style/design-handoff` implementa el sistema de diseño completo del producto (Design v1)
sobre el frontend existente de activia-trace. **No hace merge a master todavía** — quedan
gaps funcionales documentados en §6. El merge lo decide el equipo cuando esos gaps estén
cerrados o la rama sea aprobada.

Repo: `github.com/NicolasHassanP/Active-Trace-NLA`
Branch: `style/design-handoff` (ya pusheada)

---

## 2. Cómo levantar el proyecto

### Backend (Docker)
```bash
# Desde la raíz del repo
docker compose up -d

# Verificar que la API responde
curl http://localhost:8000/health
```

### Seed de usuarios demo (correr UNA VEZ por entorno)
```bash
docker cp backend/seed_demo_users.py active-trace-nla-api-1:/app/
docker exec active-trace-nla-api-1 python seed_demo_users.py
```

Crea 4 usuarios en el tenant Demo (`TENANT_ID = 8531f634-3f1f-45da-9549-2f801d85c39b`):

| Email | Password | Rol | Nombre |
|-------|----------|-----|--------|
| coordinador@demo.com | Demo1234! | COORDINADOR | Mariana Suárez |
| profesor@demo.com | Demo1234! | PROFESOR | Sofía Ledesma |
| alumno@demo.com | Demo1234! | ALUMNO | Joaquín Sosa |
| admin@demo.com | Admin1234! | ADMIN | Lucia Ferrer |

El script es **idempotente** — se puede correr varias veces sin duplicar datos.

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5174
```

El Vite proxy ya tiene configurado `/api` → `localhost:8000`.

---

## 3. Sistema de diseño implementado

### 3.1 Design tokens
Fuente única de verdad en `frontend/src/shared/styles/design-tokens.ts`.
También extendidos en `frontend/tailwind.config.js`.

**Paleta de colores (clases Tailwind disponibles):**
| Clase | Valor | Uso |
|-------|-------|-----|
| `text-ink` | `#1d2330` | Texto principal |
| `text-mut` | `#6b7280` | Texto secundario |
| `text-faint` | `#9ca3af` | Texto terciario / labels |
| `border-line` | `#e5e7eb` | Bordes suaves |
| `border-line2` | `#f3f4f6` | Bordes de filas de tabla |
| `bg` | `#f7f8fb` | Fondo global |
| `text-ind` / `bg-ind` | `#4f46e5` | Primario indigo |
| `text-ind2` / `bg-ind2` | `#4338ca` | Primario indigo oscuro |
| `bg-indBg` | `#eef0ff` | Fondo hover/active nav |
| `text-ok` / `bg-okBg` | `#16a34a / #ecfdf3` | Éxito |
| `text-warn` / `bg-warnBg` | `#e7515a / #fff1f0` | Error/peligro |
| `text-amber2` / `bg-amberBg` | `#d97706 / #fef6e7` | Advertencia |
| `text-vio` / `bg-vioBg` | `#7c3aed / #f5f3ff` | Info/especial |

**Radii:**
- `rounded-card` → `14px`
- `rounded-btn` → `10px`
- `rounded-tag` → `6px`

**Sombras:**
- `shadow-card` → `0 1px 4px rgba(16,24,40,.06)`
- `shadow-card-hover` → `0 4px 16px rgba(16,24,40,.10)`
- `shadow-modal` → `0 20px 60px rgba(16,24,40,.25)`

**Tipografía:** Manrope (Google Fonts, cargado en `frontend/src/index.css`).

**Gradientes de avatar por rol:**
| Rol | Gradiente |
|-----|-----------|
| COORDINADOR | `linear-gradient(150deg, #818cf8, #4338ca)` |
| PROFESOR | `linear-gradient(150deg, #34d399, #0a9488)` |
| ALUMNO | `linear-gradient(150deg, #fbbf24, #d97706)` |
| ADMIN | `linear-gradient(150deg, #f472b6, #be185d)` |
| FINANZAS | `linear-gradient(150deg, #34d399, #047857)` |
| TUTOR | `linear-gradient(150deg, #60a5fa, #2563eb)` |
| NEXO | `linear-gradient(150deg, #a78bfa, #7c3aed)` |

### 3.2 Componentes UI modificados o creados

Todos en `frontend/src/shared/components/ui/`:

| Componente | Estado | Notas |
|------------|--------|-------|
| `Button.tsx` | Modificado | variants: primary/secondary; sizes: sm/md |
| `Badge.tsx` | Modificado | variants: success/warning/danger/info |
| `Card.tsx` + CardHeader + CardTitle | Modificado | `rounded-card shadow-card border-line` |
| `EmptyState.tsx` | Modificado | Chip icono 54px, centrado |
| `PageHeader.tsx` | Modificado | h1 22px extrabold, subtitle |
| `StatusBadge.tsx` | Modificado | Colores inline según estado semántico |
| `KpiCard.tsx` | **Nuevo** | icon + value 26px + label + sub + variant |
| `TableWrapper.tsx` | **Nuevo** | th uppercase 11px, td con hover `#fafbff` |
| `NavIcon.tsx` | **Nuevo** | SVG inline sin dependencia externa; 17 íconos Feather |

**`NavIcon.tsx` — íconos disponibles:**
`book`, `star`, `users`, `alert-circle`, `calendar`, `clipboard`, `bell`,
`check-square`, `bar-chart-2`, `settings`, `mail`, `dollar-sign`, `shield`,
`database`, `activity`, `eye`, `log-out`

Si necesitás agregar más, seguí el mismo patrón en `ICONS: Record<string, string[]>`
(cada valor es un array de strings `d` de path SVG).

---

## 4. Shell (layout, sidebar, topbar)

### 4.1 AppLayout (`frontend/src/features/shell/components/AppLayout.tsx`)
```
flex h-screen
├── Sidebar (252px fijo, bg-white, border-r)
└── div flex-col flex-1 overflow-hidden
    ├── Topbar (60px, blur glass)
    └── main (flex-1 overflow-y-auto, padding: 24px 28px 40px, bg: #f7f8fb)
        └── <Outlet /> ← páginas van acá, SIN max-w ni mx-auto propios
```

**Regla importante para páginas nuevas:** el `AppLayout` ya provee padding lateral y
vertical. Las páginas NO deben tener `max-w-*`, `mx-auto` ni `p-*` en su wrapper raíz.
Solo usar `space-y-*` para separación vertical entre secciones.

### 4.2 Sidebar (`frontend/src/features/shell/components/Sidebar.tsx`)
- Nav agrupado con secciones. Cada sección tiene un label en uppercase 10.5px.
- La función `groupNavItems()` agrupa los `NavItem[]` por su propiedad `group`.
- Al final del sidebar: `RoleSwitcher` (user card + botón logout).

### 4.3 Nav catalog y grupos (`frontend/src/features/shell/components/buildNav.ts`)

El catálogo `NAV_CATALOG` ya tiene asignado `group` a cada ítem:

| Grupo | Ítems | Roles |
|-------|-------|-------|
| `MI CÁTEDRA` | Mis materias, Calificaciones, Padrón, Atrasados, Equipos docentes, Seguimiento | PROFESOR/TUTOR/COORD/ADMIN |
| `INSTANCIAS` | Encuentros, Coloquios | COORD/ADMIN (+ ALUMNO en Coloquios) |
| `TRABAJO` | Avisos, Tareas, Comunicaciones, Monitor, Setup cuatrimestre | Variado por ítem |
| `FINANZAS` | Liquidaciones | FINANZAS/ADMIN |
| `ADMINISTRACIÓN` | Usuarios, Estructura académica, Auditoría | ADMIN |

**ALUMNO** actualmente ve: `INSTANCIAS / Coloquios` + `TRABAJO / Avisos`.

Para agregar ítems al ALUMNO: agregar el rol `'ALUMNO'` en el array `roles` del ítem
correspondiente en `NAV_CATALOG`, y asegurarse de que el route guard en `App.tsx`
también lo incluya.

El tipo `NavItem` está en `frontend/src/features/shell/types/index.ts`:
```ts
interface NavItem {
  label: string
  path: string
  roles: Role[]
  icon?: string
  group?: string  // ← agregado en esta rama
}
```

### 4.4 RoleSwitcher (`frontend/src/features/shell/components/RoleSwitcher.tsx`)
- Trigger button: avatar + nombre + rol (expandible si el usuario tiene múltiples roles).
- Logout button: ícono → a la derecha del trigger. Usa `useLogout()` de
  `frontend/src/features/auth/hooks/useLogout.ts`.
- Dropdown de roles: aparece solo si `roles.length > 1`.

### 4.5 Topbar (`frontend/src/features/shell/components/Topbar.tsx`)
- Solo campanita de notificaciones, alineada a la derecha.
- Conectada a `useAvisosPendientes()` — muestra badge rojo con el count real.
- Al clickear navega a `/avisos`.
- **Sin buscador** (se eliminó por no tener utilidad real).

---

## 5. Login y demo users

`frontend/src/features/auth/components/LoginPage.tsx`
- Card con brand logo, formulario, y `DemoUserPicker` al pie.
- `TENANT_ID` fallback hardcodeado: `'8531f634-3f1f-45da-9549-2f801d85c39b'`.

`frontend/src/features/auth/components/DemoUserPicker.tsx`
- 4 cards clickeables (una por usuario demo).
- Al clickear llama `onSelect(email, password)` que hace login directo.
- Gradientes de avatar consistentes con `RoleSwitcher`.

---

## 6. Gap analysis — qué falta implementar

### 6.1 Mensajería interna — **PRIORIDAD ALTA** (fácil de cerrar)

**Backend C-20**: ✅ completo. Endpoints en `backend/app/api/inbox.py`:
- `GET /api/v1/inbox/` — listar hilos
- `GET /api/v1/inbox/{hilo_id}` — leer hilo
- `POST /api/v1/inbox/` — crear hilo nuevo
- `POST /api/v1/inbox/{hilo_id}/responder` — responder
- `GET /api/v1/perfil/` — perfil editable

**Frontend**: ❌ No existe. El ítem "Mensajes" en el nav (previsto para C-23) nunca
se implementó. La ruta `/mensajes` en `App.tsx` no existe → 404.

**Para cerrar:**
1. Crear `frontend/src/features/mensajeria/` con estructura feature-based.
2. Registrar ruta `/mensajes` en `App.tsx`.
3. Agregar ítem al nav catalog con `group: 'TRABAJO'` y roles apropiados.
4. Roles que deben verlo: PROFESOR, TUTOR, COORDINADOR, ADMIN (al menos).

### 6.2 Vista estado académico ALUMNO — **PRIORIDAD MEDIA**

**Backend**: ❌ No existe endpoint dedicado. No hay `GET /alumno/estado-academico`
ni `/calificaciones/mis-notas`. El ALUMNO actualmente puede:
- Ver convocatorias de coloquios y reservar turno (`/coloquios`)
- Confirmar avisos (`/avisos`)

Pero NO puede ver sus propias calificaciones, materias cursadas, ni avance académico.
Está documentado en `knowledge-base/03_actores_y_roles.md` como permiso `academico:ver_propio`.

**Para cerrar:**
1. Backend: crear endpoint `GET /api/v1/alumno/estado-academico` que devuelva
   calificaciones + entregas + estado de materias del alumno autenticado.
2. Frontend: crear página y ruta `/mi-cursada` con vista de estado personal.
3. Agregar al nav catalog con `group: 'MI CURSADA'` solo para rol ALUMNO.

### 6.3 POST registrar guardia (TUTOR) — **PRIORIDAD BAJA**

`GET /api/v1/guardias` existe. El `POST` para que el TUTOR registre su propia guardia
no está implementado (anotado como PA-05 en `knowledge-base/10_preguntas_abiertas.md`).

### 6.4 Rutas admin frontend (C-24) — **BLOQUEADO** por C-18

Las rutas `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria` tienen backend
listo (en `admin_estructura.py`, `admin_usuarios.py`, `auditoria.py`) pero NO tienen
página frontend. El ADMIN las ve en el nav pero llegan a 404.

**No implementar hasta que el profesor autorice C-18 (liquidaciones).**

---

## 7. Errores TypeScript pre-existentes (NO de esta rama)

Al correr `npm run typecheck` aparecen ~20 errores. **Ninguno fue introducido por esta
rama** — están en features de calificaciones, comunicaciones y padron que existían
antes. Verificado con `git stash` en sesión anterior.

Archivos afectados:
- `src/features/calificaciones/components/*` — cast `Error → DomainError`
- `src/features/comunicaciones/components/*` — cast `Error → DomainError`
- `src/features/padron/components/*` — cast `Error → DomainError`
- `src/__tests__/c22Routing.integration.test.tsx` — mock de `AuthContextValue` incompleto
- `src/features/comunicaciones/pages/__tests__/ComunicacionesPage.test.tsx` — ídem

No bloquean el build de producción (Vite los ignora en `build`), solo `tsc --noEmit`.

---

## 8. Archivos cambiados en esta rama vs master

```
backend/seed_demo_users.py                            ← NUEVO
frontend/tailwind.config.js                           ← modificado (tokens)
frontend/src/index.css                                ← modificado (Manrope, scrollbar)
frontend/src/App.tsx                                  ← modificado (route guard coloquios + ALUMNO)
frontend/src/shared/styles/design-tokens.ts           ← NUEVO
frontend/src/shared/components/ui/Button.tsx          ← modificado
frontend/src/shared/components/ui/Badge.tsx           ← modificado
frontend/src/shared/components/ui/Card.tsx            ← modificado
frontend/src/shared/components/ui/EmptyState.tsx      ← modificado
frontend/src/shared/components/ui/PageHeader.tsx      ← modificado
frontend/src/shared/components/ui/StatusBadge.tsx     ← modificado
frontend/src/shared/components/ui/KpiCard.tsx         ← NUEVO
frontend/src/shared/components/ui/TableWrapper.tsx    ← NUEVO
frontend/src/shared/components/ui/NavIcon.tsx         ← NUEVO
frontend/src/shared/components/ui/index.ts            ← modificado (exports nuevos)
frontend/src/features/auth/components/LoginPage.tsx   ← modificado (rediseño + DemoUserPicker)
frontend/src/features/auth/components/DemoUserPicker.tsx ← NUEVO
frontend/src/features/shell/types/index.ts            ← modificado (group en NavItem)
frontend/src/features/shell/components/AppLayout.tsx  ← modificado
frontend/src/features/shell/components/Sidebar.tsx    ← modificado (grupos nav)
frontend/src/features/shell/components/Topbar.tsx     ← modificado (solo campanita)
frontend/src/features/shell/components/RoleSwitcher.tsx ← modificado (logout integrado)
frontend/src/features/shell/components/buildNav.ts    ← modificado (grupos + ALUMNO)
# Todas las páginas — eliminado max-w-* y mx-auto del wrapper raíz:
frontend/src/features/atrasados/pages/AtrasadosPage.tsx
frontend/src/features/avisos/pages/AvisosPage.tsx
frontend/src/features/calificaciones/pages/CalificacionesPage.tsx
frontend/src/features/coloquios/pages/ColoquiosPage.tsx
frontend/src/features/comunicaciones/pages/ComunicacionesPage.tsx
frontend/src/features/encuentros-coord/pages/EncuentrosPage.tsx
frontend/src/features/equipos/pages/EquiposPage.tsx
frontend/src/features/materias/pages/MateriasPage.tsx
frontend/src/features/monitores/pages/MonitorPage.tsx
frontend/src/features/padron/pages/PadronPage.tsx
frontend/src/features/seguimiento/pages/SeguimientoPage.tsx
frontend/src/features/setup-cuatrimestre/pages/SetupCuatrimestrePage.tsx
frontend/src/features/tareas/pages/TareasPage.tsx
```

---

## 9. Próximos pasos sugeridos para el agente que continúe

En orden de prioridad y facilidad:

1. **Mensajería frontend** — backend listo, solo falta UI. Crear feature
   `frontend/src/features/mensajeria/` con `InboxPage.tsx`, registrar `/mensajes`
   en `App.tsx`, agregar al nav catalog.

2. **Vista ALUMNO estado académico** — requiere endpoint backend nuevo + página
   frontend. Leer `knowledge-base/03_actores_y_roles.md` §3.3 y
   `knowledge-base/11_historias_de_usuario.md` HU-47 antes de implementar.

3. **Admin routes frontend** (solo si C-18 está autorizado) — crear páginas para
   `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria`. Los backends
   `admin_estructura.py`, `admin_usuarios.py`, `auditoria.py` ya existen.

4. **Merge a master** — una vez cerrados los gaps 1 y 2 (o con aprobación del equipo).

---

## 10. Convenciones a respetar

- Conventional Commits: `tipo(scope): mensaje`. **Sin** `Co-Authored-By` ni atribución a IA.
- Componentes React: PascalCase, sin `any`, sin class components.
- Sin `max-w-*` ni `mx-auto` en wrappers raíz de páginas — el AppLayout provee el padding.
- Todo ítem nuevo del nav necesita: entrada en `NAV_CATALOG` (con `group`) + route guard en `App.tsx`.
- El logout vive en `RoleSwitcher.tsx`, no en el Topbar.
- Errores TS pre-existentes: no arreglar en esta rama, ya están catalogados arriba.
