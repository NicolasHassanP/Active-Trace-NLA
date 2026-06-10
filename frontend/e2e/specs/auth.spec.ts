import { test, expect } from '@playwright/test'
import { LoginPage } from '../pages/LoginPage'
import { Shell } from '../pages/Shell'
import { DEMO_USERS, type DemoRole } from '../fixtures/users'

const ROLES: DemoRole[] = ['COORDINADOR', 'PROFESOR', 'ALUMNO', 'ADMIN']

test.describe('auth', () => {
  for (const role of ROLES) {
    test(`login as ${role} enters the shell`, async ({ page }) => {
      const user = DEMO_USERS[role]
      const login = new LoginPage(page)
      const shell = new Shell(page)

      await login.goto()
      await login.loginWith(user.email, user.password)

      await shell.expectVisible()
      // Left the /login route after a successful login.
      await expect(page).not.toHaveURL(/\/login/)
      // Sidebar has at least one nav item for an authenticated user.
      expect((await shell.navLabels()).length).toBeGreaterThan(0)
    })
  }

  test('logout returns to /login', async ({ page }) => {
    const login = new LoginPage(page)
    const shell = new Shell(page)
    const user = DEMO_USERS.COORDINADOR

    await login.goto()
    await login.loginWith(user.email, user.password)
    await shell.expectVisible()

    await shell.logout()

    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible()
  })

  test('protected route without session redirects to /login', async ({ page }) => {
    // Fresh context (no auth cookie) → ProtectedRoute should bounce to /login.
    await page.goto('/monitor')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: 'Ingresar' })).toBeVisible()
  })

  test('login with wrong credentials shows error', async ({ page }) => {
    const login = new LoginPage(page)
    await login.goto()
    await login.loginWith('coordinador@demo.com', 'WRONG-password-1!')
    await login.expectError()
    await expect(page).toHaveURL(/\/login/)
  })
})
