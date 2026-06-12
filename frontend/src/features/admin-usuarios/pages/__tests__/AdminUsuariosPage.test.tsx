/**
 * Tests for AdminUsuariosPage.
 * Scenarios: gate Forbidden403 for non-ADMIN, content visible for ADMIN.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AdminUsuariosPage from '../AdminUsuariosPage'
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

describe('AdminUsuariosPage', () => {
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

  it('renders Forbidden403 for non-ADMIN roles (PROFESOR)', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['PROFESOR'] })
    render(<AdminUsuariosPage />, { wrapper: makeWrapper() })
    expect(screen.getByText('403')).toBeInTheDocument()
  })

  it('renders Forbidden403 for COORDINADOR', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['COORDINADOR'] })
    render(<AdminUsuariosPage />, { wrapper: makeWrapper() })
    expect(screen.getByText('403')).toBeInTheDocument()
  })

  it('renders Forbidden403 for FINANZAS', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['FINANZAS'] })
    render(<AdminUsuariosPage />, { wrapper: makeWrapper() })
    expect(screen.getByText('403')).toBeInTheDocument()
  })

  it('renders content for ADMIN role', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminUsuariosPage />, { wrapper: makeWrapper() })
    expect(screen.queryByText('403')).not.toBeInTheDocument()
    expect(screen.getByTestId('admin-usuarios-page')).toBeInTheDocument()
  })

  it('shows page heading for ADMIN', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminUsuariosPage />, { wrapper: makeWrapper() })
    // PageHeader renders an h1 with "Usuarios"; section h2 says "Usuarios del tenant"
    const headings = screen.getAllByRole('heading', { name: /usuarios/i })
    expect(headings.length).toBeGreaterThan(0)
  })
})
