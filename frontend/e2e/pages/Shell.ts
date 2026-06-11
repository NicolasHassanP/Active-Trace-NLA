import { expect, type Page } from '@playwright/test'

/**
 * Page object for the app shell (Sidebar + Topbar + main content area).
 * Navigation uses the sidebar NavLinks; logout uses the RoleSwitcher button.
 */
export class Shell {
  constructor(private readonly page: Page) {}

  nav() {
    return this.page.getByRole('navigation', { name: 'Navegación principal' })
  }

  async expectVisible(): Promise<void> {
    await expect(this.nav()).toBeVisible({ timeout: 15_000 })
  }

  /** Click a sidebar nav item by its visible label. */
  async navigateTo(label: string): Promise<void> {
    await this.nav().getByRole('link', { name: label, exact: true }).click()
  }

  /** True if a sidebar nav item with the given label is present. */
  async hasNavItem(label: string): Promise<boolean> {
    return (await this.nav().getByRole('link', { name: label, exact: true }).count()) > 0
  }

  /** Returns the visible text labels of all sidebar nav links. */
  async navLabels(): Promise<string[]> {
    await this.expectVisible()
    return this.nav().getByRole('link').allInnerTexts()
  }

  /** Log out via the RoleSwitcher logout button. */
  async logout(): Promise<void> {
    await this.page.getByRole('button', { name: 'Cerrar sesión' }).click()
  }

  /** Assert a page header with the given title is shown (PageHeader h1). */
  async expectPageTitle(title: string): Promise<void> {
    await expect(this.page.getByRole('heading', { level: 1, name: title })).toBeVisible({
      timeout: 15_000,
    })
  }
}
