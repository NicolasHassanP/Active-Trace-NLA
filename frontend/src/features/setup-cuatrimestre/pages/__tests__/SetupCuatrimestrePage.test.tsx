/**
 * TDD — SetupCuatrimestrePage.
 * Task 7.11 — RED first.
 *
 * Scenarios:
 * - COORDINADOR sees the wizard (access granted)
 * - ADMIN sees the wizard (access granted)
 * - PROFESOR is blocked (access denied / 403)
 * - First step is displayed on load
 * - Completing step 0 shows step 1 (sequential advance)
 * - When a step errors, it stays on current step (no advance)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SetupCuatrimestrePage from '../SetupCuatrimestrePage'

// Mock useAuth to control roles
vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))
import { useAuth } from '@/features/auth/hooks/useAuth'

// Mock all step components to keep tests simple
vi.mock('../../components/PasoCohorte', () => ({
  default: ({ onSuccess }: { onSuccess: (id: string) => void }) => (
    <div data-testid="paso-cohorte-mock">
      <button onClick={() => onSuccess('coh-1')}>Completar cohorte</button>
    </div>
  ),
}))
vi.mock('../../components/PasoClonarEquipo', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <div data-testid="paso-clonar-equipo-mock">
      <button onClick={onSuccess}>Completar clonar</button>
    </div>
  ),
}))
vi.mock('../../components/PasoAsignaciones', () => ({
  default: ({ onSuccess, onError }: { onSuccess: () => void; onError: (m: string) => void }) => (
    <div data-testid="paso-asignaciones-mock">
      <button onClick={onSuccess}>Completar asignaciones</button>
      <button onClick={() => onError('Error de prueba')}>Forzar error</button>
    </div>
  ),
}))
vi.mock('../../components/PasoVigencias', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <div data-testid="paso-vigencias-mock">
      <button onClick={onSuccess}>Completar vigencias</button>
    </div>
  ),
}))
vi.mock('../../components/PasoProgramas', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <div data-testid="paso-programas-mock">
      <button onClick={onSuccess}>Completar programas</button>
    </div>
  ),
}))
vi.mock('../../components/PasoFechas', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <div data-testid="paso-fechas-mock">
      <button onClick={onSuccess}>Completar fechas</button>
    </div>
  ),
}))
vi.mock('../../components/PasoAvisoBienvenida', () => ({
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <div data-testid="paso-aviso-bienvenida-mock">
      <button onClick={onSuccess}>Publicar aviso</button>
    </div>
  ),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: qc },
      createElement(MemoryRouter, null, children),
    )
}

beforeEach(() => vi.clearAllMocks())

describe('SetupCuatrimestrePage — role gating', () => {
  it('renders wizard for COORDINADOR', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText(/Setup de cuatrimestre/i)).toBeInTheDocument(),
    )
  })

  it('renders wizard for ADMIN', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'admin@test.com', roles: ['ADMIN'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['ADMIN'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText(/Setup de cuatrimestre/i)).toBeInTheDocument(),
    )
  })

  it('blocks PROFESOR with 403 message', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u3', email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['PROFESOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByText('403')).toBeInTheDocument())
    expect(screen.queryByText(/Setup de cuatrimestre/i)).not.toBeInTheDocument()
  })
})

describe('SetupCuatrimestrePage — sequential wizard', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
  })

  it('shows step 0 (cohorte) initially', async () => {
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByTestId('paso-cohorte-mock')).toBeInTheDocument(),
    )
  })

  it('advances to step 1 after completing step 0', async () => {
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('paso-cohorte-mock')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Completar cohorte'))

    await waitFor(() =>
      expect(screen.getByTestId('paso-clonar-equipo-mock')).toBeInTheDocument(),
    )
  })

  it('stays on current step when error occurs (no advance)', async () => {
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    // Complete steps 0 and 1 to reach step 2 (asignaciones)
    await waitFor(() => expect(screen.getByTestId('paso-cohorte-mock')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Completar cohorte'))
    await waitFor(() => expect(screen.getByTestId('paso-clonar-equipo-mock')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Completar clonar'))
    await waitFor(() => expect(screen.getByTestId('paso-asignaciones-mock')).toBeInTheDocument())

    // Trigger error on step 2
    fireEvent.click(screen.getByText('Forzar error'))

    // Step must remain the same — asignaciones still visible
    await waitFor(() =>
      expect(screen.getByTestId('paso-asignaciones-mock')).toBeInTheDocument(),
    )
  })

  it('shows completion message after last step', async () => {
    render(<SetupCuatrimestrePage />, { wrapper: makeWrapper() })
    const stepButtons = [
      'Completar cohorte',
      'Completar clonar',
      'Completar asignaciones',
      'Completar vigencias',
      'Completar programas',
      'Completar fechas',
      'Publicar aviso',
    ]
    for (const btnText of stepButtons) {
      await waitFor(() => expect(screen.getByText(btnText)).toBeInTheDocument())
      fireEvent.click(screen.getByText(btnText))
    }
    await waitFor(() =>
      expect(screen.getByText(/cuatrimestre configurado/i)).toBeInTheDocument(),
    )
  })
})
