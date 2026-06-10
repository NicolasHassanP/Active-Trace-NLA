/**
 * Auth fixtures — provide a page already authenticated as a given role.
 *
 * IMPORTANT — why each test logs in fresh (no shared storageState):
 * The backend uses refresh-token ROTATION WITH REUSE DETECTION
 * (backend/app/repositories/refresh_session_repository.py): presenting a
 * consumed refresh cookie revokes the ENTIRE token family. The app calls
 * POST /auth/refresh on every page load to re-mint its in-memory access token.
 *
 * If multiple parallel browser contexts shared a single storageState (one
 * refresh cookie), the first /auth/refresh would rotate it and the rest would
 * replay a consumed cookie → family revoked → all sessions dropped to /login.
 *
 * So every test gets its OWN login → its OWN cookie family. This is correct
 * security behavior on the backend, not a workaround for a bug.
 */
import { test as base, type Page } from '@playwright/test'
import { DEMO_USERS, type DemoRole } from './users'
import { LoginPage } from '../pages/LoginPage'

interface RoleFixtures {
  /** A page already authenticated as the requested role. */
  authedPage: Page
  /** The role this spec file runs as. Override via test.use({ role: 'ADMIN' }). */
  role: DemoRole
}

export const test = base.extend<RoleFixtures>({
  role: ['COORDINADOR', { option: true }],

  authedPage: async ({ browser, role }, use) => {
    const user = DEMO_USERS[role]
    const context = await browser.newContext()
    const page = await context.newPage()

    const login = new LoginPage(page)
    await login.goto()
    await login.loginWith(user.email, user.password)
    await login.expectLoggedIn()

    await use(page)
    await context.close()
  },
})

export { expect } from '@playwright/test'
