/**
 * Tests for AdminEstructuraPage.
 * Scenarios: gate Forbidden403 for non-ADMIN, tabs visible for ADMIN.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AdminEstructuraPage from '../AdminEstructuraPage'
import * as useAuthModule from '@/features/auth/hooks/useAuth'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc },
      createElement(MemoryRouter, {}, children)
    )
  return wrapper
}

vi.mock('@/features/auth/hooks/useAuth')

describe('AdminEstructuraPage', () => {
  const baseAuth = {
    user: null,
    tenantId: 't1',
    isInitializing: false,
    isAuthenticated: true,
    isImpersonating: false,
    impersonatedName: null,
    login: vi.fn(),
    logout: vi.fn(),
    impersonarUsuario: vi.fn(),
    finalizarImpersonacion: vi.fn(),
  }

  it('renders Forbidden403 for non-ADMIN roles', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['PROFESOR'] })
    render(<AdminEstructuraPage />, { wrapper: makeWrapper() })
    expect(screen.getByText('403')).toBeInTheDocument()
  })

  it('renders content for ADMIN role', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminEstructuraPage />, { wrapper: makeWrapper() })
    expect(screen.queryByText('403')).not.toBeInTheDocument()
    expect(screen.getByTestId('admin-estructura-page')).toBeInTheDocument()
  })

  it('shows tabs for carreras, materias, cohortes', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminEstructuraPage />, { wrapper: makeWrapper() })
    expect(screen.getByRole('tab', { name: /carreras/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /materias/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /cohortes/i })).toBeInTheDocument()
  })
})
