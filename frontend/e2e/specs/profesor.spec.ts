import { test, expect } from '../fixtures/auth.fixture'
import { Shell } from '../pages/Shell'
import {
  PadronPage,
  CalificacionesPage,
  AtrasadosPage,
  ComunicacionesPage,
} from '../pages/FeaturePage'

// Critical path: importar → analizar → comunicar, as PROFESOR.
test.use({ role: 'PROFESOR' })

test.describe('profesor — critical path', () => {
  test('Padrón loads', async ({ authedPage }) => {
    const padron = new PadronPage(authedPage)
    await padron.goto()
    await padron.expectLoaded()
    // Selector section for materia/cohorte is present.
    await expect(authedPage.getByRole('heading', { name: 'Materia y Cohorte' })).toBeVisible()
  })

  test('Calificaciones loads', async ({ authedPage }) => {
    const cal = new CalificacionesPage(authedPage)
    await cal.goto()
    await cal.expectLoaded()
  })

  test('Atrasados loads', async ({ authedPage }) => {
    const atr = new AtrasadosPage(authedPage)
    await atr.goto()
    await atr.expectLoaded()
  })

  test('Comunicaciones loads with tabs', async ({ authedPage }) => {
    const com = new ComunicacionesPage(authedPage)
    await com.goto()
    await com.expectLoaded()
    await expect(com.tab('componer')).toBeVisible()
    await expect(com.tab('historial')).toBeVisible()
    // PROFESOR is not an approval role → no "pendientes" tab.
    await expect(com.tab('pendientes')).toHaveCount(0)
  })

  test('full nav sweep: each MI CÁTEDRA page renders', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/dashboard')
    await shell.expectVisible()

    // Profesor sees these sidebar items.
    expect(await shell.hasNavItem('Padrón')).toBe(true)
    expect(await shell.hasNavItem('Calificaciones')).toBe(true)
    expect(await shell.hasNavItem('Atrasados')).toBe(true)
    expect(await shell.hasNavItem('Comunicaciones')).toBe(true)

    await shell.navigateTo('Calificaciones')
    await shell.expectPageTitle('Calificaciones')

    await shell.navigateTo('Padrón')
    await shell.expectPageTitle('Importación de Padrón')
  })
})
