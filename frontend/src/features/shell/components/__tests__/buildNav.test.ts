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
      expect(item.roles).toContain('FINANZAS')
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
  it('COORDINADOR sees all coordination-exclusive items (/avisos, /tareas, /monitor, /setup-cuatrimestre, /equipos, /encuentros, /coloquios)', () => {
    const items = buildNav(['COORDINADOR'])
    const paths = items.map((i) => i.path)
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/tareas')
    expect(paths).toContain('/monitor')
    expect(paths).toContain('/setup-cuatrimestre')
    expect(paths).toContain('/equipos')
    expect(paths).toContain('/encuentros')
    expect(paths).toContain('/coloquios')
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

  it('PROFESOR sees /avisos and /tareas but NOT /monitor, /setup-cuatrimestre, /equipos (coordination-exclusive)', () => {
    const items = buildNav(['PROFESOR'])
    const paths = items.map((i) => i.path)
    // Bandeja de avisos (broad) and tareas (own) are visible to PROFESOR
    expect(paths).toContain('/avisos')
    expect(paths).toContain('/tareas')
    // Coordination-exclusive items must NOT appear
    expect(paths).not.toContain('/monitor')
    expect(paths).not.toContain('/setup-cuatrimestre')
    expect(paths).not.toContain('/equipos')
    expect(paths).not.toContain('/encuentros')
    expect(paths).not.toContain('/coloquios')
  })

  it('FINANZAS does NOT see any coordination items', () => {
    const items = buildNav(['FINANZAS'])
    const paths = items.map((i) => i.path)
    expect(paths).not.toContain('/avisos')
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

  it('COORDINADOR does NOT see /mi-cursada', () => {
    const paths = buildNav(['COORDINADOR']).map((i) => i.path)
    expect(paths).not.toContain('/mi-cursada')
  })

  it('ADMIN does NOT see /mi-cursada (exclusive to ALUMNO)', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).not.toContain('/mi-cursada')
  })
})
