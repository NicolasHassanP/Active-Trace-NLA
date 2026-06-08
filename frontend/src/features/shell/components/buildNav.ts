/**
 * buildNav — pure function that filters the nav catalog by user roles.
 *
 * The catalog is a declarative NavItem[] — each item lists which roles can see it.
 * Empty roles array on item means "visible to all authenticated users".
 *
 * Destinations are placeholders until C-22/C-23/C-24 register their routes.
 */
import type { Role } from '@/features/auth/types'
import type { NavItem } from '../types'

/**
 * Declarative nav catalog.
 * Each item's `roles` lists who can see it.
 * ALUMNO and NEXO have no items until their modules exist (C-22+).
 */
export const NAV_CATALOG: NavItem[] = [
  // ── MI CURSADA (ALUMNO) ──────────────────────────────────
  {
    label: 'Mi cursada',
    path: '/mi-cursada',
    roles: ['ALUMNO'],
    icon: 'book',
    group: 'MI CURSADA',
  },
  // ── MI CÁTEDRA ──────────────────────────────────────────
  {
    label: 'Mis materias',
    path: '/materias',
    roles: ['PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'book',
    group: 'MI CÁTEDRA',
  },
  {
    label: 'Calificaciones',
    path: '/calificaciones',
    roles: ['PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'star',
    group: 'MI CÁTEDRA',
  },
  {
    label: 'Padrón',
    path: '/padron',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'users',
    group: 'MI CÁTEDRA',
  },
  {
    label: 'Atrasados',
    path: '/atrasados',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'alert-circle',
    group: 'MI CÁTEDRA',
  },
  {
    label: 'Equipos docentes',
    path: '/equipos',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'users',
    group: 'MI CÁTEDRA',
  },
  {
    label: 'Seguimiento',
    path: '/seguimiento',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'eye',
    group: 'MI CÁTEDRA',
  },
  // ── INSTANCIAS ───────────────────────────────────────────
  {
    label: 'Encuentros',
    path: '/encuentros',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'calendar',
    group: 'INSTANCIAS',
  },
  {
    label: 'Coloquios',
    path: '/coloquios',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'clipboard',
    group: 'INSTANCIAS',
  },
  {
    label: 'Mis coloquios',
    path: '/mis-coloquios',
    roles: ['ALUMNO'],
    icon: 'clipboard',
    group: 'INSTANCIAS',
  },
  // ── TRABAJO ──────────────────────────────────────────────
  {
    label: 'Avisos',
    path: '/avisos',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN', 'ALUMNO', 'FINANZAS'],
    icon: 'bell',
    group: 'TRABAJO',
  },
  {
    label: 'Tareas',
    path: '/tareas',
    roles: ['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'check-square',
    group: 'TRABAJO',
  },
  {
    label: 'Mensajes',
    path: '/mensajes',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'mail',
    group: 'TRABAJO',
  },
  {
    label: 'Comunicaciones',
    path: '/comunicaciones',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'mail',
    group: 'TRABAJO',
  },
  {
    label: 'Monitor',
    path: '/monitor',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'bar-chart-2',
    group: 'TRABAJO',
  },
  {
    label: 'Setup cuatrimestre',
    path: '/setup-cuatrimestre',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'settings',
    group: 'TRABAJO',
  },
  // ── FINANZAS ─────────────────────────────────────────────
  {
    label: 'Liquidaciones',
    path: '/liquidaciones',
    roles: ['FINANZAS', 'ADMIN'],
    icon: 'dollar-sign',
    group: 'FINANZAS',
  },
  // ── ADMINISTRACIÓN ───────────────────────────────────────
  {
    label: 'Usuarios',
    path: '/admin/usuarios',
    roles: ['ADMIN'],
    icon: 'shield',
    group: 'ADMINISTRACIÓN',
  },
  {
    label: 'Estructura académica',
    path: '/admin/estructura',
    roles: ['ADMIN'],
    icon: 'database',
    group: 'ADMINISTRACIÓN',
  },
  {
    label: 'Auditoría',
    path: '/admin/auditoria',
    roles: ['ADMIN'],
    icon: 'activity',
    group: 'ADMINISTRACIÓN',
  },
]

/**
 * Returns the nav items visible to the given roles.
 * Multi-role users see the union of items for all their roles, without duplicates.
 */
export function buildNav(roles: Role[]): NavItem[] {
  if (roles.length === 0) return []

  const seen = new Set<string>()
  const result: NavItem[] = []

  for (const item of NAV_CATALOG) {
    if (seen.has(item.path)) continue
    // item.roles empty = visible to all; otherwise must intersect with user roles
    const isVisible =
      item.roles.length === 0 || item.roles.some((r) => roles.includes(r))
    if (isVisible) {
      seen.add(item.path)
      result.push(item)
    }
  }

  return result
}
