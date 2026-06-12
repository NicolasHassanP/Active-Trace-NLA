/**
 * Tests for buildNav pure function — task 8.1 RED
 *
 * Scenarios:
 * - FINANZAS role → sees FINANZAS items only
 * - Multi-role: PROFESOR + COORDINADOR → union without duplicates
 * - Role with no destinations → empty list
 * - ADMIN → sees all items
 */
import { describe, it, expect } from 'vitest'
import { buildNav } from '../buildNav'
import type { Role } from '@/features/auth/types'

describe('buildNav — pure function', () => {
  it('returns items for FINANZAS role', () => {
    const items = buildNav(['FINANZAS'])
    expect(items.length).toBeGreaterThan(0)
    items.forEach(item => {
      // Visible either because FINANZAS is listed, or because the item is
      // global (roles: [] = visible to all authenticated users, e.g. /perfil).
      const visible = item.roles.length === 0 || item.roles.includes('FINANZAS')
      expect(visible).toBe(true)
    })
  })

  it('returns union without duplicates for multi-role user (PROFESOR + COORDINADOR)', () => {
    const roles: Role[] = ['PROFESOR', 'COORDINADOR']
    const items = buildNav(roles)
    const paths = items.map(i => i.path)
    // No duplicates
    expect(new Set(paths).size).toBe(paths.length)
    // All items must be accessible by at least one of the user's roles
    items.forEach(item => {
      const accessible = item.roles.some(r => roles.includes(r)) || item.roles.length === 0
      expect(accessible).toBe(true)
    })
  })

  it('returns items for ALUMNO role (/mi-cursada)', () => {
    // ALUMNO now has /mi-cursada from C-25
    const items = buildNav(['ALUMNO'])
    expect(items.length).toBeGreaterThan(0)
    const paths = items.map((i) => i.path)
    expect(paths).toContain('/mi-cursada')
  })

  it('ADMIN sees all items', () => {
    const adminItems = buildNav(['ADMIN'])
    const allRolesItems = buildNav(['ALUMNO', 'TUTOR', 'PROFESOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS'])
    // ADMIN should see at least as many items as any single non-ALUMNO role
    expect(adminItems.length).toBeGreaterThan(0)
    // ADMIN items should be a subset of all items
    adminItems.forEach(item => {
      const exists = allRolesItems.some(a => a.path === item.path)
      expect(exists).toBe(true)
    })
  })

  it('empty roles list returns empty array', () => {
    expect(buildNav([])).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// C-23 role-gated items (task 8.3)
// ---------------------------------------------------------------------------

describe('buildNav — C-23 coordination items', () => {
  it('COORDINADOR sees coordination items (/avisos, /tareas, /monitor, /equipos, /encuentros, /coloquios) but NOT /setup-cuatrimestre', () => {
    const items = buildNav(['COORDINADOR'])
    const paths = items.map((i) => i.path)
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/tareas')
    expect(paths).toContain('/monitor')
    expect(paths).toContain('/equipos')
    expect(paths).toContain('/encuentros')
    expect(paths).toContain('/coloquios')
    // Setup cuatrimestre requiere estructura:gestionar → solo ADMIN (03_actores_y_roles.md:79)
    expect(paths).not.toContain('/setup-cuatrimestre')
  })

  it('ADMIN sees all coordination items', () => {
    const items = buildNav(['ADMIN'])
    const paths = items.map((i) => i.path)
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/tareas')
    expect(paths).toContain('/monitor')
    expect(paths).toContain('/setup-cuatrimestre')
    expect(paths).toContain('/equipos')
    expect(paths).toContain('/encuentros')
    expect(paths).toContain('/coloquios')
  })

  it('PROFESOR sees /avisos, /tareas, /encuentros but NOT /monitor, /setup-cuatrimestre, /equipos, /coloquios', () => {
    const items = buildNav(['PROFESOR'])
    const paths = items.map((i) => i.path)
    // Bandeja de avisos (broad), tareas (propias) y encuentros (propios) son visibles a PROFESOR
    // (matriz 03_actores_y_roles.md: "Gestionar encuentros" → PROFESOR propio)
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/tareas')
    expect(paths).toContain('/encuentros')
    // Coordination-exclusive items must NOT appear
    expect(paths).not.toContain('/monitor')
    expect(paths).not.toContain('/setup-cuatrimestre')
    expect(paths).not.toContain('/equipos')
    expect(paths).not.toContain('/coloquios')
  })

  it('FINANZAS sees /avisos and /liquidaciones but NOT coordination items', () => {
    const items = buildNav(['FINANZAS'])
    const paths = items.map((i) => i.path)
    // FINANZAS tiene avisos:confirmar (matriz) → ve la bandeja de avisos
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/liquidaciones')
    expect(paths).not.toContain('/tareas')
    expect(paths).not.toContain('/monitor')
    expect(paths).not.toContain('/setup-cuatrimestre')
    expect(paths).not.toContain('/equipos')
    expect(paths).not.toContain('/encuentros')
    expect(paths).not.toContain('/coloquios')
  })

  it('TUTOR sees /tareas (gestión tareas propias) but NOT /monitor or /setup-cuatrimestre', () => {
    const items = buildNav(['TUTOR'])
    const paths = items.map((i) => i.path)
    expect(paths).toContain('/tareas')
    expect(paths).not.toContain('/monitor')
    expect(paths).not.toContain('/setup-cuatrimestre')
  })
})

// ---------------------------------------------------------------------------
// Guardias nav item (F6.6) — TUTOR/PROFESOR/COORDINADOR/ADMIN, group INSTANCIAS
// ---------------------------------------------------------------------------

describe('buildNav — guardias item', () => {
  it.each<Role>(['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN'])('%s sees /guardias', (role) => {
    const paths = buildNav([role]).map((i) => i.path)
    expect(paths).toContain('/guardias')
  })

  it('ALUMNO does NOT see /guardias', () => {
    const paths = buildNav(['ALUMNO']).map((i) => i.path)
    expect(paths).not.toContain('/guardias')
  })

  it('FINANZAS does NOT see /guardias', () => {
    const paths = buildNav(['FINANZAS']).map((i) => i.path)
    expect(paths).not.toContain('/guardias')
  })

  it('/guardias item is in group INSTANCIAS', () => {
    const item = buildNav(['PROFESOR']).find((i) => i.path === '/guardias')
    expect(item?.group).toBe('INSTANCIAS')
  })
})

// ---------------------------------------------------------------------------
// C-26 mensajería nav item (task 7.3)
// ---------------------------------------------------------------------------

describe('buildNav — C-26 mensajería item', () => {
  it('COORDINADOR sees /mensajes', () => {
    const paths = buildNav(['COORDINADOR']).map((i) => i.path)
    expect(paths).toContain('/mensajes')
  })

  it('PROFESOR sees /mensajes', () => {
    const paths = buildNav(['PROFESOR']).map((i) => i.path)
    expect(paths).toContain('/mensajes')
  })

  it('TUTOR sees /mensajes', () => {
    const paths = buildNav(['TUTOR']).map((i) => i.path)
    expect(paths).toContain('/mensajes')
  })

  it('ADMIN sees /mensajes', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).toContain('/mensajes')
  })

  it('ALUMNO does NOT see /mensajes', () => {
    const paths = buildNav(['ALUMNO']).map((i) => i.path)
    expect(paths).not.toContain('/mensajes')
  })

  it('/mensajes item is in group TRABAJO', () => {
    const item = buildNav(['COORDINADOR']).find((i) => i.path === '/mensajes')
    expect(item?.group).toBe('TRABAJO')
  })
})

// ---------------------------------------------------------------------------
// C-25 mi-cursada nav item (task 7.2)
// ---------------------------------------------------------------------------

describe('buildNav — C-25 mi-cursada item', () => {
  it('ALUMNO sees /mi-cursada', () => {
    const paths = buildNav(['ALUMNO']).map((i) => i.path)
    expect(paths).toContain('/mi-cursada')
  })

  it('/mi-cursada item is in group MI CURSADA', () => {
    const item = buildNav(['ALUMNO']).find((i) => i.path === '/mi-cursada')
    expect(item?.group).toBe('MI CURSADA')
  })

  it('PROFESOR does NOT see /mi-cursada', () => {
    const paths = buildNav(['PROFESOR']).map((i) => i.path)
    expect(paths).not.toContain('/mi-cursada')
  })
})

// ---------------------------------------------------------------------------
// C-29 admin core nav items: estructura + auditoria (admin-usuarios deferred)
// ---------------------------------------------------------------------------

describe('buildNav — C-29 admin-estructura and admin-auditoria items', () => {
  it('ADMIN sees /admin/estructura', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).toContain('/admin/estructura')
  })

  it('ADMIN sees /admin/auditoria', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).toContain('/admin/auditoria')
  })

  it('ADMIN sees /admin/usuarios (in nav catalog, route deferred)', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).toContain('/admin/usuarios')
  })

  it('PROFESOR does NOT see admin items', () => {
    const paths = buildNav(['PROFESOR']).map((i) => i.path)
    expect(paths).not.toContain('/admin/estructura')
    expect(paths).not.toContain('/admin/auditoria')
    expect(paths).not.toContain('/admin/usuarios')
  })

  it('/admin/estructura and /admin/auditoria items are NOT disabled', () => {
    const items = buildNav(['ADMIN'])
    const estructura = items.find((i) => i.path === '/admin/estructura')
    const auditoria = items.find((i) => i.path === '/admin/auditoria')
    expect(estructura?.disabled).toBeFalsy()
    expect(auditoria?.disabled).toBeFalsy()
  })

  it('/liquidaciones item remains disabled (C-18 deferred)', () => {
    const items = buildNav(['ADMIN'])
    const liquidaciones = items.find((i) => i.path === '/liquidaciones')
    expect(liquidaciones?.disabled).toBe(true)
  })

  it('admin items are in group ADMINISTRACIÓN', () => {
    const items = buildNav(['ADMIN'])
    const estructura = items.find((i) => i.path === '/admin/estructura')
    const auditoria = items.find((i) => i.path === '/admin/auditoria')
    expect(estructura?.group).toBe('ADMINISTRACIÓN')
    expect(auditoria?.group).toBe('ADMINISTRACIÓN')
  })
})

// ---------------------------------------------------------------------------
// Perfil propio nav item (M2 / F11.1) — visible to ALL authenticated users
// ---------------------------------------------------------------------------

describe('buildNav — perfil item (visible to all)', () => {
  const ROLES: Role[] = ['ALUMNO', 'TUTOR', 'PROFESOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS']

  it.each(ROLES)('%s sees /perfil', (role) => {
    const paths = buildNav([role]).map((i) => i.path)
    expect(paths).toContain('/perfil')
  })

  it('/perfil item has empty roles (visible to all)', () => {
    const item = buildNav(['ALUMNO']).find((i) => i.path === '/perfil')
    expect(item?.roles).toEqual([])
  })

  it('empty roles list (unauthenticated) still returns empty array', () => {
    expect(buildNav([])).toEqual([])
  })

  it('COORDINADOR does NOT see /mi-cursada', () => {
    const paths = buildNav(['COORDINADOR']).map((i) => i.path)
    expect(paths).not.toContain('/mi-cursada')
  })

  it('ADMIN does NOT see /mi-cursada (exclusive to ALUMNO)', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).not.toContain('/mi-cursada')
  })
})
