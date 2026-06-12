/**
 * Tests for AdminAuditoriaPage.
 * Scenarios: Forbidden403 gate for non-ADMIN, renders for ADMIN.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AdminAuditoriaPage from '../AdminAuditoriaPage'
import * as useAuthModule from '@/features/auth/hooks/useAuth'

vi.mock('@/features/auth/hooks/useAuth')

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc },
      createElement(MemoryRouter, {}, children)
    )
  return wrapper
}

const baseAuth = {
  user: null, tenantId: 't1', isInitializing: false, isAuthenticated: true,
  isImpersonating: false, impersonatedName: null,
  login: vi.fn(), logout: vi.fn(), impersonarUsuario: vi.fn(), finalizarImpersonacion: vi.fn(),
}

describe('AdminAuditoriaPage', () => {
  afterEach(() => vi.restoreAllMocks())

  it('renders Forbidden403 for non-ADMIN roles', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['PROFESOR'] })
    render(<AdminAuditoriaPage />, { wrapper: makeWrapper() })
    expect(screen.getByText('403')).toBeInTheDocument()
  })

  it('renders content for ADMIN role', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminAuditoriaPage />, { wrapper: makeWrapper() })
    expect(screen.queryByText('403')).not.toBeInTheDocument()
    expect(screen.getByTestId('admin-auditoria-page')).toBeInTheDocument()
  })

  it('shows tab navigation for eventos and metricas', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({ ...baseAuth, roles: ['ADMIN'] })
    render(<AdminAuditoriaPage />, { wrapper: makeWrapper() })
    expect(screen.getByRole('tab', { name: /eventos/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /métricas/i })).toBeInTheDocument()
  })
})
