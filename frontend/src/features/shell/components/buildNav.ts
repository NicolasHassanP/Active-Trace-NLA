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
  // --- PROFESOR ---
  {
    label: 'Mis materias',
    path: '/materias',
    roles: ['PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'book',
  },
  {
    label: 'Calificaciones',
    path: '/calificaciones',
    roles: ['PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'star',
  },
  // C-22: Padrón — PROFESOR·TUTOR·COORDINADOR·ADMIN
  {
    label: 'Padrón',
    path: '/padron',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'users',
  },
  // C-22: Atrasados — PROFESOR·TUTOR·COORDINADOR·ADMIN
  {
    label: 'Atrasados',
    path: '/atrasados',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'alert-circle',
  },
  // --- COORDINADOR ---
  {
    label: 'Equipos docentes',
    path: '/equipos',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'users',
  },
  {
    label: 'Encuentros',
    path: '/encuentros',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'calendar',
  },
  {
    label: 'Coloquios',
    path: '/coloquios',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'clipboard',
  },
  // C-23: Avisos — bandeja (PROFESOR·TUTOR·COORDINADOR·ADMIN); gestión inside page
  {
    label: 'Avisos',
    path: '/avisos',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'bell',
  },
  // C-23: Tareas internas — mis-tareas (TUTOR·PROFESOR·COORDINADOR·ADMIN); admin panel inside page
  {
    label: 'Tareas',
    path: '/tareas',
    roles: ['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN'],
    icon: 'check-square',
  },
  // C-23: Monitor — COORDINADOR·ADMIN only
  {
    label: 'Monitor',
    path: '/monitor',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'bar-chart-2',
  },
  // C-23: Setup cuatrimestre — COORDINADOR·ADMIN only
  {
    label: 'Setup cuatrimestre',
    path: '/setup-cuatrimestre',
    roles: ['COORDINADOR', 'ADMIN'],
    icon: 'settings',
  },
  // C-22: Comunicaciones expanded to PROFESOR·TUTOR (comunicacion:enviar)
  {
    label: 'Comunicaciones',
    path: '/comunicaciones',
    roles: ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'mail',
  },
  // --- FINANZAS ---
  {
    label: 'Liquidaciones',
    path: '/liquidaciones',
    roles: ['FINANZAS', 'ADMIN'],
    icon: 'dollar-sign',
  },
  // --- ADMIN ---
  {
    label: 'Usuarios',
    path: '/admin/usuarios',
    roles: ['ADMIN'],
    icon: 'shield',
  },
  {
    label: 'Estructura académica',
    path: '/admin/estructura',
    roles: ['ADMIN'],
    icon: 'database',
  },
  {
    label: 'Auditoría',
    path: '/admin/auditoria',
    roles: ['ADMIN'],
    icon: 'activity',
  },
  // --- TUTOR ---
  {
    label: 'Seguimiento',
    path: '/seguimiento',
    roles: ['TUTOR', 'COORDINADOR', 'ADMIN'],
    icon: 'eye',
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
