import { test, expect } from '../fixtures/auth.fixture'
import { Shell } from '../pages/Shell'

test.use({ role: 'ADMIN' })

/**
 * INTENTIONAL 404s (documented in HANDOFF.md §6.4):
 * The ADMIN nav exposes items whose pages are deferred (C-24 / C-18).
 * These paths MUST render NotFound404 — this is expected, NOT a bug.
 */
const INTENTIONAL_404_ROUTES = [
  '/admin/usuarios',
  '/admin/estructura',
  '/admin/auditoria',
  '/liquidaciones',
]

test.describe('admin', () => {
  test('admin sees the full nav', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/dashboard')
    await shell.expectVisible()

    // ADMIN union of capabilities: spot-check items from several groups.
    expect(await shell.hasNavItem('Mis materias')).toBe(true)
    expect(await shell.hasNavItem('Calificaciones')).toBe(true)
    expect(await shell.hasNavItem('Padrón')).toBe(true)
    expect(await shell.hasNavItem('Equipos docentes')).toBe(true)
    expect(await shell.hasNavItem('Monitor')).toBe(true)
    expect(await shell.hasNavItem('Coloquios')).toBe(true)
    expect(await shell.hasNavItem('Setup cuatrimestre')).toBe(true)
    // Admin-group items present in nav (even though they 404 — see below).
    expect(await shell.hasNavItem('Usuarios')).toBe(true)
    expect(await shell.hasNavItem('Estructura académica')).toBe(true)
    expect(await shell.hasNavItem('Auditoría')).toBe(true)
    expect(await shell.hasNavItem('Liquidaciones')).toBe(true)
  })

  test('admin reaches an implemented page (Monitor)', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/monitor')
    await shell.expectPageTitle('Monitor general de actividades')
  })

  for (const route of INTENTIONAL_404_ROUTES) {
    test(`deferred route ${route} shows NotFound404 (intentional)`, async ({ authedPage }) => {
      await authedPage.goto(route)
      // The NotFound404 screen renders "404" + the spanish message.
      await expect(authedPage.getByRole('heading', { name: '404' })).toBeVisible()
      await expect(authedPage.getByText('Página no encontrada')).toBeVisible()
    })
  }

  test('Setup cuatrimestre (ADMIN-only) loads', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/setup-cuatrimestre')
    await shell.expectPageTitle('Setup de cuatrimestre')
  })
})
