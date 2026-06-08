# Handoff — rama `style/design-handoff`

> Documento de estado de la rama. Leé esto ANTES de tocar cualquier archivo del frontend.
> Última actualización: 2026-06-08.

---

## 1. Qué es esta rama

`style/design-handoff` implementa el sistema de diseño completo del producto (Design v1)
sobre el frontend existente de activia-trace, más las features C-25, C-26 y C-27.
**No hace merge a master todavía** — quedan C-18 y C-24 bloqueados por preguntas de negocio abiertas.

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
| `MI CURSADA` | Mi cursada | ALUMNO |
| `MI CÁTEDRA` | Mis materias, Calificaciones, Padrón, Atrasados, Equipos docentes, Seguimiento | PROFESOR/TUTOR/COORD/ADMIN |
| `INSTANCIAS` | Encuentros, Coloquios | COORD/ADMIN (+ ALUMNO en Coloquios) |
| `TRABAJO` | Avisos, Tareas, Comunicaciones, Mensajes, Monitor, Setup cuatrimestre | Variado por ítem |
| `FINANZAS` | Liquidaciones | FINANZAS/ADMIN |
| `ADMINISTRACIÓN` | Usuarios, Estructura académica, Auditoría | ADMIN |

**ALUMNO** ve: `MI CURSADA / Mi cursada` + `INSTANCIAS / Coloquios` + `TRABAJO / Avisos`.

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
  group?: string
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

## 6. Features implementadas (estado completo)

### 6.1 Mensajería interna (C-26) — ✅ implementada

**Backend C-20**: ✅ Endpoints en `/api/v1/inbox/`.
**Frontend**: ✅ `features/mensajeria/` completa — `InboxPage`, layout master-detail,
`HilosList`, `HiloView`, `NuevoHiloForm`, `ResponderForm`.
Ruta `/mensajes` registrada en `App.tsx`. Ítem en nav grupo `TRABAJO`.
Roles: PROFESOR, TUTOR, COORDINADOR, ADMIN.

### 6.2 Portal alumno / Mi cursada (C-25) — ✅ implementada

**Backend**: ✅ `GET /api/v1/alumno/estado-academico` con `require_permission("academico:ver_propio")`.
**Frontend**: ✅ `features/mi-cursada/` completa — `MiCursadaPage`, `AvanceKpis`,
`MateriasCursadasTable`, `ColoquiosReservadosPanel`.
Ruta `/mi-cursada` registrada en `App.tsx`. Ítem en nav grupo `MI CURSADA`, solo ALUMNO.

### 6.3 Historial de comunicaciones (C-27) — ✅ implementada

**Backend**: ✅ `GET /comunicaciones/mis-envios` con paginación y filtro de estado.
Índice compuesto `(tenant_id, enviado_por, created_at DESC)` via migración Alembic.
**Frontend**: ✅ `ComunicacionesHistorial` con tabla + filtro de estado. `ComunicacionesPage`
tiene tabs "Componer" | "Historial".

### 6.4 Rutas admin frontend (C-24) — ❌ BLOQUEADO por C-18

Las rutas `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria` tienen backend
listo pero NO tienen página frontend. El ADMIN las ve en el nav pero llegan a 404.
**No implementar hasta resolver PA-22/PA-23 y autorizar C-18 (liquidaciones).**

---

## 7. Changes pendientes

| Change | Estado | Bloqueado por |
|--------|--------|---------------|
| C-18 `liquidaciones-y-honorarios` | `[ ]` pendiente | PA-22/PA-23 (preguntas de negocio sin cerrar) |
| C-24 `frontend-finanzas-y-admin` | `[ ]` pendiente | C-18 |

No hay otros changes pendientes. Todo lo implementable está archivado.

---

## 8. TypeScript — estado limpio

`npx tsc --noEmit` pasa con **0 errores** (corregidos en 2026-06-08).

Patrones corregidos:
- `error as DomainError` → `error as unknown as DomainError` (9 componentes)
- `total_filas` → `filas_total` en `SyncMoodlePanel` y tests de padrón
- `alumno_id` → `entrada_padron_id` en fixtures de atrasados
- `AuthContextValue` mock completo con `tenantId` en tests de routing
- Fixtures de `MonitorFila`, `InboxHiloRead`, `MisEquiposItem` completadas en tests
- `makeAxiosError` return type corregido en `domainError.test.ts`
- `act` import no usado removido; `onClear` prop renombrado a `_onClear`

---

## 9. Archivos cambiados en esta rama vs master (resumen)

**Backend:**
- `backend/seed_demo_users.py`, `seed_demo_estructura.py`, `seed_rbac_demo.py` — seeds demo
- `backend/app/api/v1/routers/alumno.py`, `comunicaciones.py`, varios — nuevos endpoints
- `backend/app/repositories/alumno_repository.py`, `comunicacion_repository.py` — nuevos métodos
- `backend/app/schemas/alumno.py`, `comunicacion.py` — nuevos schemas Pydantic

**Frontend — design system:**
- `tailwind.config.js`, `src/index.css`, `src/shared/styles/design-tokens.ts`
- `src/shared/components/ui/` — Button, Badge, Card, EmptyState, PageHeader, StatusBadge, KpiCard, TableWrapper, NavIcon

**Frontend — shell:**
- `src/features/shell/components/` — AppLayout, Sidebar, Topbar, RoleSwitcher, buildNav
- `src/features/auth/components/LoginPage.tsx`, `DemoUserPicker.tsx`

**Frontend — features nuevas:**
- `src/features/mensajeria/` — InboxPage + componentes (C-26)
- `src/features/mi-cursada/` — MiCursadaPage + componentes (C-25)
- `src/features/comunicaciones/components/ComunicacionesHistorial.tsx` — tabs (C-27)

**Frontend — todas las páginas existentes:** eliminado `max-w-*` y `mx-auto` del wrapper raíz.

---

## 10. Convenciones a respetar

- Conventional Commits: `tipo(scope): mensaje`. **Sin** `Co-Authored-By` ni atribución a IA.
- Componentes React: PascalCase, sin `any`, sin class components.
- Sin `max-w-*` ni `mx-auto` en wrappers raíz de páginas — el AppLayout provee el padding.
- Todo ítem nuevo del nav necesita: entrada en `NAV_CATALOG` (con `group`) + route guard en `App.tsx`.
- El logout vive en `RoleSwitcher.tsx`, no en el Topbar.
- `tsc --noEmit` debe pasar limpio — no mergear con errores TS.
