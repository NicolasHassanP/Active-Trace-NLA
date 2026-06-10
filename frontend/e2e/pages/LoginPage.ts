import { expect, type Page } from '@playwright/test'

/**
 * Page object for the login screen (/login).
 * The form posts to POST /api/v1/auth/login with the tenant in the X-Tenant
 * header (handled by the app via the hardcoded demo TENANT_ID fallback).
 */
export class LoginPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/login')
    await expect(this.page.getByRole('heading', { name: 'Ingresar' })).toBeVisible()
  }

  /** Fill the email/password form and submit. */
  async loginWith(email: string, password: string): Promise<void> {
    await this.page.locator('#email').fill(email)
    await this.page.locator('#password').fill(password)
    await this.page.getByRole('button', { name: 'Ingresar' }).click()
  }

  /** Use a DemoUserPicker quick-access card by role label. */
  async loginViaPicker(roleLabel: string): Promise<void> {
    await this.page.getByRole('button', { name: new RegExp(roleLabel, 'i') }).first().click()
  }

  /** Assert the login attempt succeeded (shell sidebar is rendered). */
  async expectLoggedIn(): Promise<void> {
    await expect(this.page.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible({
      timeout: 15_000,
    })
  }

  /** Assert the credentials error banner is shown. */
  async expectError(): Promise<void> {
    await expect(this.page.getByText('Email o contraseña incorrectos')).toBeVisible()
  }
}
