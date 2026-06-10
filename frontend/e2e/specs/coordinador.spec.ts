import { test, expect } from '../fixtures/auth.fixture'
import { Shell } from '../pages/Shell'
import {
  EquiposPage,
  AvisosPage,
  TareasPage,
  MonitorPage,
  ComunicacionesPage,
} from '../pages/FeaturePage'

test.use({ role: 'COORDINADOR' })

test.describe('coordinador', () => {
  test('Equipos docentes loads with management panel', async ({ authedPage }) => {
    const equipos = new EquiposPage(authedPage)
    await equipos.goto()
    await equipos.expectLoaded()
    // COORDINADOR is a manager → gestión panel rendered.
    await expect(equipos.gestionPanel()).toBeVisible()
    await expect(authedPage.getByRole('heading', { name: 'Mis asignaciones' })).toBeVisible()
  })

  test('Avisos loads with management panel + bandeja', async ({ authedPage }) => {
    const avisos = new AvisosPage(authedPage)
    await avisos.goto()
    await avisos.expectLoaded()
    await expect(avisos.gestionPanel()).toBeVisible()
    await expect(avisos.bandeja()).toBeVisible()
    // The "Nuevo aviso" management action is available.
    await expect(authedPage.getByRole('button', { name: 'Nuevo aviso' })).toBeVisible()
  })

  test('Avisos: opening the new-aviso form reveals it', async ({ authedPage }) => {
    const avisos = new AvisosPage(authedPage)
    await avisos.goto()
    await avisos.expectLoaded()
    await authedPage.getByRole('button', { name: 'Nuevo aviso' }).click()
    // Form panel appears inside the gestión section.
    await expect(avisos.gestionPanel().locator('form')).toBeVisible()
  })

  test('Tareas loads', async ({ authedPage }) => {
    const tareas = new TareasPage(authedPage)
    await tareas.goto()
    await tareas.expectLoaded()
  })

  test('Monitor loads', async ({ authedPage }) => {
    const monitor = new MonitorPage(authedPage)
    await monitor.goto()
    await monitor.expectLoaded()
  })

  test('Comunicaciones shows approval tab for coordinador', async ({ authedPage }) => {
    const com = new ComunicacionesPage(authedPage)
    await com.goto()
    await com.expectLoaded()
    // COORDINADOR is an approval role → pendientes tab present.
    await expect(com.tab('pendientes')).toBeVisible()
  })

  test('sidebar shows coordinador-only items', async ({ authedPage }) => {
    const shell = new Shell(authedPage)
    await authedPage.goto('/dashboard')
    await shell.expectVisible()
    expect(await shell.hasNavItem('Equipos docentes')).toBe(true)
    expect(await shell.hasNavItem('Monitor')).toBe(true)
    expect(await shell.hasNavItem('Coloquios')).toBe(true)
  })
})
