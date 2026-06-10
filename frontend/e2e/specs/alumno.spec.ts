import { test, expect } from '../fixtures/auth.fixture'
import { Shell } from '../pages/Shell'
import { MiCursadaPage, MisColoquiosPage, AvisosPage } from '../pages/FeaturePage'

test.use({ role: 'ALUMNO' })

test.describe('alumno', () => {
  test('Mi cursada loads with KPIs and materias sections', async ({ authedPage }) => {
    const cursada = new MiCursadaPage(authedPage)
    await cursada.goto()
    await cursada.expectLoaded()
    await expect(cursada.materiasHeading()).toBeVisible()
    await expect(cursada.coloquiosHeading()).toBeVisible()
  })

  test('Mis coloquios (reserva view) loads', async ({ authedPage }) => {
    const coloquios = new MisColoquiosPage(authedPage)
    await coloquios.goto()
    await coloquios.expectLoaded()
  })

  test('Avisos loads for alumno (bandeja only, no gestión)', async ({ authedPage }) => {
    const avisos = new AvisosPage(authedPage)
    await avisos.goto()
    await avisos.expectLoaded()
    await expect(avisos.bandeja()).toBeVisible()
    // ALUMNO is not a manager → no gestión panel, no "Nuevo aviso".
    await expect(avisos.gestionPanel()).toHaveCount(0)
    await expect(authedPage.getByRole('button', { name: 'Nuevo aviso' })).toHaveCount(0)
  })

  test('sidebar shows alumno items only', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/dashboard')
    await shell.expectVisible()
    expect(await shell.hasNavItem('Mi cursada')).toBe(true)
    expect(await shell.hasNavItem('Mis coloquios')).toBe(true)
    expect(await shell.hasNavItem('Avisos')).toBe(true)
    // Manager-only items are NOT visible to alumno.
    expect(await shell.hasNavItem('Monitor')).toBe(false)
    expect(await shell.hasNavItem('Equipos docentes')).toBe(false)
  })
})
