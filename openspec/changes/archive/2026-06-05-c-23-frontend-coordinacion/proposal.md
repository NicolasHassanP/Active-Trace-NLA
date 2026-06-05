## Why

Los backends de coordinación y administración (C-08 equipos docentes, C-13 encuentros/guardias, C-14 evaluaciones/coloquios, C-15 avisos+acknowledgment, C-16 tareas internas, C-17 programas+fechas académicas) ya están en producción y validados, pero el rol COORDINADOR/ADMIN todavía no tiene una superficie de usuario para operarlos: hoy esos endpoints solo se consumen vía API. C-21 entregó el shell + auth y C-22 cubrió las vistas académicas del docente; falta cerrar el frente de coordinación, que es donde se arma y supervisa todo el período académico. Sin esta UI, el setup de cuatrimestre (FL-03), la publicación de avisos (FL-09), el workflow de tareas (FL-05) y la supervisión transversal quedan inaccesibles para los usuarios reales.

## What Changes

- **Equipos docentes (Épica 4)**: vista de "mis equipos" (F4.2), vista de equipo por materia×carrera×cohorte, asignación masiva (F4.4), clonado de equipo entre períodos (F4.5), modificación de vigencia general (F4.6) y exportación del equipo (F4.7). Consume `/api/v1/equipos/*`.
- **Avisos (Épica 3, F3.5 / FL-09)**: ABM de avisos con scope (global / materia / cohorte), severidad, roles destinatarios, vigencia, orden, estado activo y `require_ack`; bandeja de avisos pendientes y confirmación de lectura (acknowledgment). Consume `/api/v1/avisos/*`.
- **Tareas internas (Épica 8 / FL-05)**: vista de "mis tareas", panel de administración de coordinación con filtros, alta de tarea, delegación, cambio de estado (workflow) y comentarios. Consume `/api/v1/tareas/*`.
- **Monitores transversales (Épica 2, F2.7 y F2.9)**: vista general de actividades del tenant (coordinación/admin) con filtros (materia, regional, comisión, búsqueda, estado, rango de fechas) y exportación. Consume `/api/v1/analisis/monitor`.
- **Encuentros — vista coordinación/admin (F6.5)** y **Guardias (F6.6 consulta global)**: vista transversal de instancias de encuentros del tenant y registro/consulta de guardias con exportación. Consume `/api/v1/encuentros/*` y `/api/v1/guardias/*`.
- **Coloquios (Épica 7)**: panel de métricas (F7.1), listado de convocatorias (F7.4), creación de convocatoria (F7.3), importación de candidatos (F7.2), cierre, agenda de reservas y registro consolidado de resultados (F7.5). Consume `/api/v1/coloquios/*`.
- **Setup de cuatrimestre (FL-03)**: flujo guiado que orquesta cohorte → clonar equipo → ajustar asignaciones → vigencias → programas de materia (F5.3) → fechas de evaluaciones (F5.4) → aviso de bienvenida. Consume `/api/v1/equipos`, `/api/v1/programas`, `/api/v1/fechas-academicas`, `/api/v1/avisos` y la estructura académica existente.
- **Routing y navegación**: nuevas rutas lazy en `App.tsx` envueltas en `ProtectedRoute` con gating de rol (COORDINADOR/ADMIN según matriz RBAC) y activación de los ítems de nav placeholder ya presentes en `buildNav.ts` (`/equipos`, `/encuentros`, `/coloquios`) más los nuevos (`/avisos`, `/tareas`, `/monitor`, `/setup-cuatrimestre`).

No hay cambios de contrato en el backend: esta change solo consume endpoints ya existentes. No hay **BREAKING**.

## Capabilities

### New Capabilities
- `equipos-frontend`: vista de mis equipos, equipo por contexto, asignación masiva, clonado, vigencia general y exportación (Épica 4).
- `avisos-frontend`: ABM de avisos con scope/severidad/vigencia/roles/ack, bandeja de pendientes y confirmación de lectura (F3.5, FL-09).
- `tareas-frontend`: mis tareas, admin de tareas con filtros, alta, delegación, workflow de estados y comentarios (Épica 8, FL-05).
- `monitores-frontend`: monitor general de actividades transversal para coordinación/admin con filtros y export (F2.7, F2.9).
- `encuentros-coordinacion-frontend`: vista transversal de encuentros del tenant y registro/consulta de guardias (F6.5, F6.6).
- `coloquios-frontend`: métricas, convocatorias, candidatos, cierre, agenda de reservas y resultados (Épica 7, FL-07 lado coordinación).
- `setup-cuatrimestre-frontend`: flujo guiado de inicio de cuatrimestre que orquesta cohorte, equipo, programas, fechas y aviso (FL-03).

### Modified Capabilities
<!-- Ninguna: esta change no modifica requisitos de specs backend existentes; solo consume sus endpoints. -->

## Impact

- **Frontend (nuevo código)**: módulos feature-based bajo `frontend/src/features/{equipos,avisos,tareas,monitores,encuentros-coord,coloquios,setup-cuatrimestre}/` siguiendo el patrón de C-22 (`types/index.ts`, `services/<name>Service.ts`, `hooks/<name>Hooks.ts`, `components/*`, `pages/*`, `__tests__`).
- **Routing/nav**: `frontend/src/App.tsx` (rutas lazy nuevas), `frontend/src/features/shell/components/buildNav.ts` (ítems de nav nuevos/gateados por rol).
- **Reutilización**: `@/shared/services/api` (Axios centralizado), `@/shared/services/domainError.ts`, `ProtectedRoute`, Sonner (`<Toaster/>` ya montado).
- **Backends consumidos (sin cambios)**: equipos-docentes, avisos, tareas-internas, encuentros, guardias, evaluacion-* (coloquios), programas-materia, fechas-academicas, análisis (monitor).
- **Dependencias npm**: ninguna nueva esperada (stack ya instalado: React 18, TS, Vite, TanStack Query, RHF+Zod, Tailwind, Axios, Sonner, Zustand, Vitest+Testing Library).
- **Governance**: BAJO (feature de frontend, sin dominios críticos). Autonomía total en propose; las OPEN QUESTIONS sobre contratos ambiguos se surfacearán en design.md para resolver antes de apply.
